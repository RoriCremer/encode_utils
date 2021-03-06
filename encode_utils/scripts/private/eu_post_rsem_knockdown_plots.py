#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###
# © 2018 The Board of Trustees of the Leland Stanford Junior University
# Nathaniel Watson
# nathankw@stanford.edu
###

OUTPUT_FILE = "submitted.txt"

description = """
Posts the barplots from an RSEM analysis to the corresponding library objects. The input file is
formatted similarly to the Excel submission sheet. Additionally, submits the analysis protocol to
the experiment object. An output file is generated by the name of {outfile} is created, which is
in the same format as the input file, but with the additional field 'jpeg_dcc_uuid' that provides
the DCC document ID of the knockdown plot that is posted.
""".format(outfile=OUTPUT_FILE)

import argparse
import glob
import pdb

from encode_utils.connection import Connection
# contains the arguments needed for logging in to the ENCODE Portal, including which env.
from encode_utils.parent_argparser import dcc_login_parser


def get_parser():
    parser = argparse.ArgumentParser(
        parents=[dcc_login_parser],
        description=description,
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-i", "--infile", required=True, help="""
    The tab-delimited input file that indicates which barplots to submit and where to submit them.
    Format is:
      1) dcc_exp_id
       2) dcc_rep_id #uses this to get the library accession.
      3) barplot_path
    The first line must be a field-header line starting with '#'. The dcc_exp_id and dcc_rep_id
    can be any valid ENCODE identifiers for the respective objects.
  """)

    parser.add_argument("-p", "--protocol-uuid", required=True, help="""
    A DCC document UUID specifying the RSEM analysis protocol that explains how the RSEM analysis
    and plotting was performed. i.e. ba93f5cc-a470-41a2-842f-2cb3befbeb60.
  """)
    return parser


def main():
    """Program
    """
    parser = get_parser()
    args = parser.parse_args()
    dcc_mode = args.dcc_mode
    infile = args.infile
    protocol_uuid = args.protocol_uuid

    # connect to DCC
    conn = Connection(dcc_mode)

    barplot_description = "Barplot showing the expression of the given gene in the control vs. the treatment. Expression is given in Transcripts Per Million (TPM) and was generated by version 1.2.30 of RSEM's rsem-calculate-expression script."
    fh = open(infile, 'r')
    header = fh.readline().strip("\n")
    if not header.startswith("#"):
        raise Exception("First line of input file must be a field-header line starting with a '#'.")
    dico = {}  # key: library accession, value: {barplot: local_barplot_path, line: line_from_input_file}
    # store a list of all exp IDs seen in input file so we can later link the
    # analysis protocol doc to the exp.
    exp_encids = []
    for line in fh:
        line = line.strip("\n")
        if not line.strip():
            continue
        line = line.split("\t")
        dcc_exp_id = line[0].strip()
        if dcc_exp_id not in exp_encids:
            exp_encids.append(dcc_exp_id)
        dcc_rep_id = line[1].strip()
        rep_json = conn.get(rep_id, ignore404=False)
        dcc_lib_id = rep_json["library"]["accession"]
        barplot = line[2].strip()
        dico[dcc_lib_id] = {
            "barplot": barplot,
            "line": line
        }
    fh.close()

    fout = open(OUTPUT_FILE, 'w')
    fout.write(header + "\tjpeg_dcc_uuid\n")
    count = 0
    for lib_id in dico:
        #  count += 1
        barplot = dico[lib_id]["barplot"]
        download_filename = lib_id + "_relative_knockdown.jpeg"
        # download_filename is the name the user will get when they downoad the
        # file from the ENCODE Portal.
        dcc_uuid = conn.post_document(
            download_filename=download_filename,
            document=barplot,
            document_type="data QA",
            document_description=barplot_description)
        line = dico[lib_id]["line"]
        line.append(dcc_uuid)
        fout.write("\t".join(line) + "\n")
        # link document to library
        conn.link_document(rec_id=lib_id, dcc_document_uuid=dcc_uuid)
    fout.close()

    print("Linking RSEM analysis and plotting protocol document to each experiment")
    for exp in exp_encids:
        conn.link_document(rec_id=exp, document_id=protocol_uuid)


if __name__ == "__main__":
    main()
