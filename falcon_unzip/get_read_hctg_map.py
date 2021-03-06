from pypeflow.simple_pwatcher_bridge import (PypeProcWatcherWorkflow, MyFakePypeThreadTaskBase,
        makePypeLocalFile, fn, PypeTask)
import argparse
import logging
import os
import sys

def make_dirs(d):
    if not os.path.isdir(d):
        os.makedirs(d)

def generate_read_to_hctg_map(self):
    rawread_id_file = fn( self.rawread_id_file )
    pread_id_file = fn( self.pread_id_file )
    read_to_contig_map = fn( self.read_to_contig_map )

    pread_did_to_rid = open(pread_id_file).read().split('\n')
    rid_to_oid = open(rawread_id_file).read().split('\n')

    h_ctg_edges = fn( self.h_ctg_edges )
    p_ctg_edges = fn( self.p_ctg_edges )

    h_ctg_ids = set()
    with open(fn(self.h_ctg_ids)) as f:
        for row in f:
            row = row.strip()
            h_ctg_ids.add( row )

    pread_to_contigs = {}

    for fnanme in ( p_ctg_edges, h_ctg_edges):
        with open(fnanme) as f:
            for row in f:
                row = row.strip().split()
                ctg = row[0]
                if len(ctg.split('_')) > 1 and ctg not in h_ctg_ids:
                    continue
                n1 = row[1]
                n2 = row[2]
                pid1 = int(n1.split(':')[0])
                pid2 = int(n2.split(':')[0])
                rid1 = pread_did_to_rid[pid1].split('/')[1]
                rid2 = pread_did_to_rid[pid2].split('/')[1]
                rid1 = int(int(rid1)/10)
                rid2 = int(int(rid2)/10)
                oid1 = rid_to_oid[rid1]
                oid2 = rid_to_oid[rid2]
                k1 = (pid1, rid1, oid1)
                pread_to_contigs.setdefault( k1, set() )
                pread_to_contigs[ k1 ].add( ctg )
                k2 = (pid2, rid2, oid2)
                pread_to_contigs.setdefault( k2, set() )
                pread_to_contigs[ k2 ].add( ctg )

    with open(read_to_contig_map, 'w') as f:
        for k in pread_to_contigs:
            pid, rid, oid = k
            for ctg in list(pread_to_contigs[ k ]):
                print >>f, '%09d %09d %s %s' % (pid, rid, oid, ctg)

def get_read_hctg_map(asm_dir, hasm_dir, read_to_contig_map_fn):
    wf = PypeProcWatcherWorkflow(
            max_jobs=12, # TODO: Why was NumThreads ever set? There is only one task!
    )

    rawread_id_file = makePypeLocalFile(os.path.join(asm_dir, 'read_maps/dump_rawread_ids/rawread_ids'))
    pread_id_file = makePypeLocalFile(os.path.join(asm_dir, 'read_maps/dump_pread_ids/pread_ids'))
    h_ctg_edges = makePypeLocalFile(os.path.join(hasm_dir, 'all_h_ctg_edges'))
    p_ctg_edges = makePypeLocalFile(os.path.join(hasm_dir, 'all_p_ctg_edges'))
    h_ctg_ids = makePypeLocalFile( os.path.join(hasm_dir, "all_h_ctg_ids"))
    #make_dirs(os.path.dirname(os.path.abspath(read_to_contig_map_fn)) # Workflow does this.

    read_to_contig_map_plf = makePypeLocalFile(read_to_contig_map_fn)

    inputs = { 'rawread_id_file': rawread_id_file,
               'pread_id_file': pread_id_file,
               'h_ctg_edges': h_ctg_edges,
               'p_ctg_edges': p_ctg_edges,
               'h_ctg_ids': h_ctg_ids}

    make_task = PypeTask(
               inputs = inputs,
               outputs = {'read_to_contig_map': read_to_contig_map_plf},
    )
    wf.addTask(make_task(generate_read_to_hctg_map))
    wf.refreshTargets() # block



def parse_args(argv):
    parser = argparse.ArgumentParser(description='generate `read_to_contig_map` that contains the \
information from the chain of mapping: (contig id, last col) -> (internal p-read id) -> (internal raw-read id) -> (original read id)\n \
it assumes the 2-asm-falcon/read_maps ... /dump_rawread_ids/rawread_ids and /dump_pread_ids/pread_ids are already generated',
              formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--output', type=str, default="./4-quiver/read_maps/read_to_contig_map", help='output file')
    args = parser.parse_args(argv[1:])
    return args

def main(argv=sys.argv):
    logging.basicConfig()
    args = parse_args(argv)
    output = args.output
    #rawread_dir = os.path.abspath('0-rawreads')
    #pread_dir = os.path.abspath('1-preads_ovl')
    asm_dir = os.path.abspath('2-asm-falcon')
    hasm_dir = os.path.abspath('3-unzip')

    get_read_hctg_map(asm_dir=asm_dir, hasm_dir=hasm_dir, read_to_contig_map_fn=output)
