pita improves transcript annotation 
===================================

Pipeline to improve transcript annotation based on RNA-seq and ChIP-seq data.

At the moment, it's still a mess. It will be updated to annotate the Xenopus laevis genome with based on experimental data.

Prerequisites
------------
The following Python modules are required:
* GFF parser - http://github.com/chapmanb/bcbb/tree/master/gff
* Biopython - http://biopython.org/
* pyyaml
* networkx

Installation
------------
    # install prerequisites
    git clone git@bitbucket.org:simonvh/pita.git
    cd pita
    sudo python setup.py install
