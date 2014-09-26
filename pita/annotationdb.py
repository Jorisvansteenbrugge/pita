import os
import sys
import logging
from gimmemotifs.genome_index import GenomeIndex
from sqlalchemy import and_
from sqlalchemy.orm import joinedload
from pita import db_session
from pita.db_backend import * 
from pita.util import read_statistics

class AnnotationDb():
    def __init__(self, new=False, index=None):
        self.logger = logging.getLogger("pita")
        self.session = db_session('mysql://pita:@localhost/pita', new)
        
        if index:
            self.index = GenomeIndex(index)
        else:
            self.index = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
            self.session.flush()
            self.session.expunge_all()
    
    def add_transcript(self, name, source, exons):
        """
        Add a transcript to the database
        """

        # Sanity checks
        for e1, e2 in zip(exons[:-1], exons[1:]):
            if e1[0] != e2[0]:
                sys.stderr.write("{0} - {1}\n".format(e1, e2))
                raise ValueError, "Different chromosomes!"
            if e2[1] <= e1[2]:
                sys.stderr.write("{0} - {1}\n".format(e1, e2))
                raise ValueError, "exons overlap, or in wrong order"
            if e1[3] != e2[3]:
                sys.stderr.write("{0} - {1}\n".format(e1, e2))
                raise ValueError, "strands don't match"
       
        chrom = exons[0][0]
        strand = exons[0][-1]

        for exon in exons:
            seq = ""
            if self.index:
                seq = self.index.get_sequence(chrom, exon[1], exon[2], strand)
            exon = get_or_create(self.session, Feature,
                             chrom = chrom,
                             start = exon[1],
                             end = exon[2],
                             strand = strand,
                             ftype = "exon",
                             seq = seq
                             ) 
            exon.evidences.append(Evidence(name=name, source=source))

        for start,end in [(e1[2], e2[1]) for e1, e2 in zip(exons[0:-1], exons[1:])]:
            sj = get_or_create(self.session, Feature,
                             chrom = chrom,
                             start = start,
                             end = end,
                             strand = strand,
                             ftype = "splice_junction"
                             ) 
            sj.evidences.append(Evidence(name=name, source=source))
        self.session.commit()
    
    def get_features(self, ftype=None, chrom=None):
        self.session.query(Feature).options(
                joinedload('read_counts')).all()
        
        query = self.session.query(Feature)
        if chrom:
            query = query.filter(Feature.chrom == chrom)
        if ftype:
            query = query.filter(Feature.ftype == ftype)
        features = [f for f in query]
        return features

    def get_exons(self, chrom=None):
        return self.get_features(ftype="exon", chrom=chrom)
    
    def get_splice_junctions(self, chrom=None):
        return self.get_features(ftype="splice_junction", chrom=chrom)

    def get_long_exons(self, l):
        query = self.session.query(Feature)
        query = query.filter(Feature.ftype == 'exon')
        query = query.filter(Feature.end - Feature.start >= l)
        return [e for e in query if len(e.evidences) == 1]

#    def get_evidence_count(self, exon):
#        query = self.session.query(Feature)
#        query = query.filter(Feature.ftype == 'exon')
#        query = query.filter(Feature.end - Feature.start >= l)
#        return [e for e in query if len(e.evidences) == 1]
    
    def get_read_statistics(self, fnames, name, span="exon", extend=(0,0), nreads=None):
        from fluff.fluffio import get_binned_stats
        from tempfile import NamedTemporaryFile

        tmp = NamedTemporaryFile()
        estore = {}
        self.logger.debug("Writing exons to file")
        for exon in self.get_exons():
            start = exon.start
            end = exon.end
            if exon.strand == "-":
                start -= extend[1]
                end += extend[0]
            else:
                start -= extend[0]
                end += extend[1]
            if start < 0:
                start = 0

            estore["%s:%s-%s" % (exon.chrom, start, end)] = exon
            tmp.write("%s\t%s\t%s\t%s\t%s\t%s\n" % (
                exon.chrom,
                start,
                end,
                str(exon),
                0,
                exon.strand
            ))
        tmp.flush()

        if type("") == type(fnames):
            fnames = [fnames]

        for i, fname in enumerate(fnames):
            
            read_source = get_or_create(self.session, ReadSource, name=name, source=fname)
            self.session.commit() 
            if fname.endswith("bam") and (not nreads or not nreads[i]):
                rmrepeats = True
                self.logger.debug("Counting reads in {0}".format(fname))
                read_source.nreads = read_statistics(fname)
            else:
                rmrepeats = False

            self.logger.debug("Getting overlap from {0}".format(fname))
            result = get_binned_stats(tmp.name, fname, 1, rpkm=False, rmdup=False, rmrepeats=False)

            self.logger.debug("Reading results, save to exon stats")

            for row in result:
                vals = row.strip().split("\t")
                e = "%s:%s-%s" % (vals[0], vals[1], vals[2])
                c = float(vals[3])
                exon = estore[e]
                
                count = get_or_create(self.session, FeatureReadCount,
                            feature_id = exon.id,
                            read_source_id = read_source.id)
                self.session.commit()
                if not count.count:
                    count.count = c
                else:
                    count.count += c

            self.session.commit()
        tmp.close()

    def get_splice_statistics(self, fnames, name):
        if type("") == type(fnames):
            fnames = [fnames]

        nrsplice = {}
        for fname in fnames:
            read_source = get_or_create(self.session, ReadSource, name=name, source=fname)
            self.session.commit()
            for line in open(fname):
                vals = line.strip().split("\t")
                print vals
                chrom = vals[0]
                start, end, c = [int(x) for x in vals[1:4]]
                strand = vals[5]
                
                splice = get_or_create(self.session, Feature,
                             chrom = chrom,
                             start = start,
                             end = end,
                             strand = strand,
                             ftype = "splice_junction"
                             ) 
    
                count = get_or_create(self.session, FeatureReadCount,
                            feature_id = splice.id,
                            read_source_id = read_source.id)
                
                if not count.count:
                    count.count = c
                else:
                    count.count += c
            
            self.session.commit()    
    
    def get_junction_exons(self, junction):
        
        left = self.session.query(Feature).filter(and_(
            Feature.chrom == junction.chrom,
            Feature.strand == junction.strand,
            Feature.end == junction.start
            ))
        
        right = self.session.query(Feature).filter(and_(
            Feature.chrom == junction.chrom,
            Feature.strand == junction.strand,
            Feature.start == junction.end
            ))

        exon_pairs = []
        for e1 in left:
            for e2 in right:
                exon_pairs.append((e1, e2))
        return exon_pairs

    def feature_stats(self, feature, identifier):
        q = self.session.query(FeatureReadCount, ReadSource).join(ReadSource)
        q = q.filter(FeatureReadCount.feature_id == feature.id)
        q = q.filter(ReadSource.name == identifier)
       
        return sum([x[0].count for x in q.all()])

    def splice_stats(self, exon1, exon2, identifier):
        q = self.session.query(Feature)
        q = q.filter(Feature.ftype == "splice_junction")
        q = q.filter(Feature.chrom == exon1.chrom)
        q = q.filter(Feature.strand == exon1.strand)
        q = q.filter(Feature.start == exon1.end)
        q = q.filter(Feature.end == exon2.start)

        splice = q.first()
        return self.feature_stats(splice, identifier)

    def nreads(self, identifier):
        q = self.session.query(ReadSource)
        q = q.filter(ReadSource.name == identifier)
        return sum([s.nreads for s in q.all()])