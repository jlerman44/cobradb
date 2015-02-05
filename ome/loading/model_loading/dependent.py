# -*- coding: utf-8 -*-

from ome import base
from ome.models import *
from ome.components import *
from ome.loading.model_loading import queries, parse

import logging

def loadModelGenes(session, model_list):
    """Load the database with all genes in the list of models"""
    
    for model in model_list:
        # find the model in the db
        model_db = queries.get_model(session, model.id)

        # find the chromosomes in the db
        chromosomes_db = queries.chromosomes_for_genome(session, model_db.genome_id)
        if len(chromosomes_db) == 0:
            logging.warn('No chromosome for model %s' % model.id)
            continue

        # load the genes
        for gene in model.genes:
            # don't ignore spontaneous
            # if gene.id == 's0001':
            #     continue
            # TODO do we have to go through chromosomes here?
            for chromosome_db in chromosomes_db: 
                created = False
                # look for genes, matching on genes locus id
                gene_db = (session
                           .query(Gene)
                           .filter(Gene.bigg_id == gene.id)
                           .filter(Gene.chromosome_id == chromosome_db.id)
                           .first())
                if gene_db is not None:
                    # check for model genes
                    if not queries.has_model_gene(session, model_db.id, gene_db.id):
                        queries.add_model_gene(session, model_db.id, gene_db.id)
                        created = True
                    continue

                # try matching on gene name
                gene_db = (session
                           .query(Gene)
                           .filter(Gene.name == gene.id)
                           .filter(Gene.chromosome_id == chromosome_db.id)
                           .first())
                if gene_db is not None:
                    # check for model genes
                    if not queries.has_model_gene(session, model_db.id, gene_db.id):
                        queries.add_model_gene(session, model_db.id, gene_db.id)
                        created = True
                    continue

                # try matching on the part of the gene id before '.'
                # TODO what is the correct way to handle this?
                gene_db = (session
                           .query(Gene)
                           .filter(Gene.name == gene.id.split('.')[0])
                           .filter(Gene.chromosome_id == chromosome_db.id)
                           .first())
                if gene_db is not None:
                    # check for model genes
                    if not queries.has_model_gene(session, model_db.id, gene_db.id):
                        queries.add_model_gene(session, model_db.id, gene_db.id)
                        created = True
                    continue

                # try matching on synonyms
                synonyms_db = (session
                               .query(Synonym)
                               .filter(Synonym.synonym == gene.id.split('.')[0])
                               .filter(Synonym.type == 'gene')
                               .all())
                match = False
                for syn_db in synonyms_db:
                    gene_db = (session
                               .query(Gene)
                               .filter(Gene.id == syn_db.ome_id)
                               .first())
                    if gene_db is not None:
                        # check for model genes
                        if not queries.has_model_gene(session, model_db.id, gene_db.id):
                            queries.add_model_gene(session, model_db.id, gene_db.id)
                            created = True
                        match = True
                        break
                        # TODO what is this?
                        # if modelquery.bigg_id == "RECON1" or modelquery.bigg_id == "iMM1415":
                        #     gene_db = (session.query(Gene).filter(Gene.id == syn.ome_id).first())
                        #     gene_db.bigg_id = gene.id
                # if we found a synonym, then we are done
                if match:
                    created = True 
                    continue
                # otherwise, add a new gene and a new model gene
                if created == True:
                    logging.warn('created should always equal false')
                    
                logging.warn('Gene not in genbank file: %s (%s) from model %s' %
                             (gene.id, gene.name, model.id))

                ome_gene = {}
                ome_gene['bigg_id'] = gene.id
                ome_gene['name'] = gene.name
                ome_gene['leftpos'] = gene.locus_start
                ome_gene['rightpos'] = gene.locus_end
                ome_gene['chromosome_id'] = chromosome_db.id
                ome_gene['name'] = gene.name
                ome_gene['strand'] = gene.strand
                ome_gene['info'] = str(gene.annotation)
                ome_gene['mapped_to_genbank'] = False

                gene_object = Gene(**ome_gene)
                session.add(gene_object)
                session.commit() # commit, so that gene_object has a primary key id
                queries.add_model_gene(session, model_db.id, gene_object.id)


def loadModelCompartmentalizedComponent(session, model_list):
    """Load the Compartments, CompartmentalizedComponents, and
    ModelCompartmentalizedComponent for each metabolite in the models in
    model_list.

    """

    for model in model_list:
        for metabolite in model.metabolites:
            try:
                metabolite_id, compartment_id = parse.split_compartment(metabolite.id)
            except Exception:
                logging.error(('Could not find compartment for metabolite %s in'
                               'model %s' % (metabolite.id, model.id)))
                continue

            # Compartment
            compartment_db = (session
                              .query(Compartment)
                              .filter(Compartment.bigg_id == compartment_id)
                              .first())
            if compartment_db is None:
                compartment_db = Compartment(bigg_id=compartment_id, name='')
                session.add(compartment_db)
                session.commit()
                
            # get the Metabolite
            metabolite_db = (session
                             .query(Metabolite)
                             .filter(Metabolite.bigg_id == metabolite_id)
                             .first())
            if metabolite_db is None:
                logging.error('Could not find Metabolite %s in the database' % metabolite.id)
                continue
                             
            # CompartmentalizedComponent
            comp_component_db = (session
                                 .query(CompartmentalizedComponent)
                                 .filter(CompartmentalizedComponent.component_id == metabolite_db.id)
                                 .filter(CompartmentalizedComponent.compartment_id == compartment_db.id)
                                 .first())
            if comp_component_db is None:
                comp_component_db = CompartmentalizedComponent(component_id=metabolite_db.id,
                                                               compartment_id=compartment_db.id)
                session.add(comp_component_db)
                session.commit()
                
            # ModelCompartmentalizedComponent
            model_db = (session
                        .query(Model)
                        .filter(Model.bigg_id == model.id)
                        .first())
            if model_db is None:
                logging.error('Could not find model %s in the database' % model.id)
                continue
            
            found_model_comp_comp = (session
                                     .query(ModelCompartmentalizedComponent)
                                     .filter(ModelCompartmentalizedComponent.compartmentalized_component_id == comp_component_db.id)
                                     .filter(ModelCompartmentalizedComponent.model_id == model_db.id)
                                     .count() > 0)
            if not found_model_comp_comp:
                new_object = ModelCompartmentalizedComponent(model_id=model_db.id,
                                                             compartmentalized_component_id=comp_component_db.id,
                                                             compartment_id=compartment_db.id)
                session.add(new_object)

def loadModelReaction(session, model_list):
    for model in model_list:
        for reaction in model.reactions:
            reaction_db = (session
                           .query(Reaction)
                           .filter(Reaction.bigg_id == reaction.id)
                           .first())
            model_db = (session
                        .query(Model)
                        .filter(Model.bigg_id == model.id)
                        .first())
            if reaction_db != None:
                has_model_reaction = (session
                                      .query(ModelReaction)
                                      .filter(ModelReaction.reaction_id == reaction_db.id)
                                      .filter(ModelReaction.model_id == model_db.id)
                                      .count() > 0)
                if not has_model_reaction:
                    new_object = ModelReaction(reaction_id=reaction_db.id,
                                               model_id=model_db.id,
                                               name=reaction.id,
                                               upper_bound=reaction.upper_bound,
                                               lower_bound=reaction.lower_bound,
                                               gene_reaction_rule=reaction.gene_reaction_rule,
                                               objective_coefficient=reaction.objective_coefficient)
                    session.add(new_object)


def loadGeneReactionMatrix(session, model_list):
    for model in model_list:
        for reaction in model.reactions:
            for gene in reaction._genes:
                # if gene.id == 's0001':
                #     continue

                model_db = (session
                            .query(Model)
                            .filter(Model.bigg_id == model.id)
                            .first())
                model_gene_db = (session
                                 .query(ModelGene)
                                 .join(Gene)
                                 .filter(Gene.bigg_id == gene.id)
                                 .filter(ModelGene.model_id == model_db.id)
                                 .first())

                if model_gene_db != None:
                    model_reaction_db = (session
                                         .query(ModelReaction)
                                         .filter(ModelReaction.name == reaction.id)
                                         .filter(ModelReaction.model_id == model_db.id)
                                         .first())
                    if not (session
                            .query(GeneReactionMatrix)
                            .filter(GeneReactionMatrix.model_gene_id == model_gene_db.id)
                            .filter(GeneReactionMatrix.model_reaction_id == model_reaction_db.id)
                            .count()):
                        new_object = GeneReactionMatrix(model_gene_id = model_gene_db.id, model_reaction_id = model_reaction_db.id)
                        session.add(new_object)
                else:
                    model_gene_db = (session
                                     .query(ModelGene)
                                     .join(Gene)
                                     .filter(Gene.name == gene.id)
                                     .filter(ModelGene.model_id == model_db.id)
                                     .first())
                    if model_gene_db != None:

                        model_reaction_db = (session
                                             .query(ModelReaction)
                                             .filter(ModelReaction.name == reaction.id)
                                             .filter(ModelReaction.model_id == model_db.id)
                                             .first())
                        if not (session.query(GeneReactionMatrix).filter(GeneReactionMatrix.model_gene_id == model_gene_db.id).filter(GeneReactionMatrix.model_reaction_id == model_reaction_db.id).count()):

                            new_object = GeneReactionMatrix(model_gene_id = model_gene_db.id, model_reaction_id = model_reaction_db.id)
                            session.add(new_object)
                    else:
                        synonymquery = (session.query(Synonym).filter(Synonym.synonym == gene.id.split(".")[0]).first())
                        if synonymquery != None:
                            if synonymquery.ome_id != None:
                                model_gene_db = (session.query(ModelGene).filter(ModelGene.gene_id == synonymquery.ome_id).filter(ModelGene.model_id == model_db.id).first())
                                model_reaction_db = (session.query(ModelReaction).filter(ModelReaction.name == reaction.id).filter(ModelReaction.model_id == model_db.id).first())

                                if model_reaction_db and model_gene_db:
                                    if not (session.query(GeneReactionMatrix).filter(GeneReactionMatrix.model_gene_id == model_gene_db.id).filter(GeneReactionMatrix.model_reaction_id == model_reaction_db.id).count()):

                                        new_object = GeneReactionMatrix(model_gene_id = model_gene_db.id, model_reaction_id = model_reaction_db.id)
                                        session.add(new_object)
                                else:
                                    print "model reaction or model gene was not found " + str(reaction.id) + " " + str(synonymquery.ome_id)
                            else:
                                print "ome id is null " + synonymquery.ome_id
                        else:
                            print "mistake", gene.id, reaction.id

def loadReactionMatrix(session, model_list):
    for model in model_list:
        for reaction in model.reactions:
            reaction_db = (session
                           .query(Reaction)
                           .filter(Reaction.bigg_id == reaction.id)
                           .first())
            if reaction_db is None:
                logging.error('Could not find reaction %s in the database' % reaction.id)
                continue
                
            for metabolite, stoich in reaction.metabolites.iteritems():
                try:
                    metabolite_id, compartment_id = parse.split_compartment(metabolite.id)
                except Exception:
                    logging.error('Could not split metabolite %s in model %s' % (metabolite.id, model.id))
                    continue
                    
                component_db = (session
                                .query(Metabolite)
                                .filter(Metabolite.bigg_id == metabolite_id)
                                .first())
                if component_db is None:
                    logging.error('Could not find metabolite %s in the database' % metabolite_id)
                    continue

                compartment_db = (session
                                  .query(Compartment)
                                  .filter(Compartment.bigg_id == compartment_id)
                                  .first())
                if compartment_db is None:
                    logging.error('Could not find compartment %s in the database' % compartment_id)
                    continue

                comp_component_db = (session
                                     .query(CompartmentalizedComponent)
                                     .filter(CompartmentalizedComponent.component_id == component_db.id)
                                     .filter(CompartmentalizedComponent.compartment_id == compartment_db.id)
                                     .first())
                if comp_component_db is None:
                    logging.error('Could not find CompartmentalizedComponent for %s in the database' % metabolite.id)
                    continue
                    
                found_reaction_matrix = (session
                                         .query(ReactionMatrix)
                                         .filter(ReactionMatrix.reaction_id == reaction_db.id)
                                         .filter(ReactionMatrix.compartmentalized_component_id == comp_component_db.id)
                                         .count() > 0)
                if not found_reaction_matrix:
                    new_object = ReactionMatrix(reaction_id=reaction_db.id,
                                                compartmentalized_component_id=comp_component_db.id,
                                                stoichiometry=stoich)
                    session.add(new_object)

def loadEscher(session):
    m = models.parse_model('iJO1366')
    for reaction in m.reactions:
        escher = Escher_Map(bigg_id = reaction.id, category = "reaction", model_name = m.id)
        session.add(escher)

def loadModelCount(session, model_list):
    for model in model_list:
        for model_id in session.query(Model.id).filter(Model.bigg_id == model.id):
            metabolite_count = (session
                                .query(ModelCompartmentalizedComponent.id)
                                .filter(ModelCompartmentalizedComponent.model_id == model_id)
                                .count())
            reaction_count = (session.query(ModelReaction.id)
                            .filter(ModelReaction.model_id == model_id)
                            .count())
            gene_count = (session.query(ModelGene.id)
                            .filter(ModelGene.model_id == model_id)       
                            .count())
            mc = ModelCount(model_id = model_id, gene_count = gene_count, metabolite_count = metabolite_count, reaction_count = reaction_count)
            session.add(mc)

def loadOldIdtoSynonyms(session, old_ids):
    for mkey, mvalue in old_ids['metabolites'].iteritems():
        ome_synonym = {'type': 'metabolite'}
        m = (session
             .query(Metabolite)
             .filter(Metabolite.bigg_id == parse.split_compartment(mkey)[0])
             .first())
        if m is not None:
            ome_synonym['ome_id'] = m.id
            ome_synonym['synonym'] = mvalue

            if (session.query(base.DataSource).filter(base.DataSource.name=="old id").count()):                   
                data_source_db = (session.query(base.DataSource).filter(base.DataSource.name=="old id").first())
                data_source_id = data_source_db.id
            else:
                data_source = base.DataSource(name="old id")
                session.add(data_source)
                session.flush()
                data_source_id = data_source.id
            ome_synonym['synonym_data_source_id'] = data_source_id
            if not (session
                    .query(base.Synonym)
                    .filter(base.Synonym.ome_id == m.id)
                    .filter(base.Synonym.synonym == mvalue)
                    .filter(base.Synonym.type == 'metabolite')
                    .first()):
                synonym = base.Synonym(**ome_synonym)
                session.add(synonym)

    ome_synonym = {}
    for rkey, rvalue in old_ids['reactions'].iteritems():
        ome_synonym = {'type':'reaction'}
        r = (session.query(Reaction).filter(Reaction.bigg_id == rkey).first())
        if r is not None:
            ome_synonym['ome_id'] = r.id
            ome_synonym['synonym'] = rvalue

            if (session.query(base.DataSource).filter(base.DataSource.name=="old id").count()):
                data_source_db = (session.query(base.DataSource).filter(base.DataSource.name=="old id").first())
                data_source_id = data_source_db.id
            else:
                data_source = base.DataSource(name="old id")
                session.add(data_source)
                session.flush()
                data_source_id = data_source.id
            ome_synonym['synonym_data_source_id'] = data_source_id
            if not (session
                    .query(base.Synonym)
                    .filter(base.Synonym.ome_id == r.id)
                    .filter(base.Synonym.synonym == rvalue)
                    .filter(base.Synonym.type == 'reaction')
                    .first()):
                synonym = base.Synonym(**ome_synonym)
                session.add(synonym)
