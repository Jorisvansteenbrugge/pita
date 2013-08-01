from pita.config import SAMTOOLS
from subprocess import Popen, PIPE

def read_statistics(fname, rmrepeat=False, rmdup=False, mapped=False):
    """ Count number of reads in BAM file.
    Optional arguments rmrepeat and rmdup do nothing for now
    """
    
    cmd = "{0} idxstats {1} | awk '{{total += $3 + $4}} END {{print total}}'"
    
    p = Popen(
             cmd.format(SAMTOOLS, fname), 
             shell=True, 
             stdout=PIPE, 
             stderr=PIPE
             )

    stdout,stderr = p.communicate()

    n = int(stdout.strip())

    return n
