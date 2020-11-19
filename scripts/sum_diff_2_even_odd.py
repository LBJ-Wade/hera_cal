#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2019 the HERA Project
# Licensed under the MIT License

from hera_cal import arithmetic

a = arithmetic.sum_diff_2_even_odd_argparser()
args = a.parse_args()

if args.nbl_per_load == "none" or args.nbl_per_load == 0:
    args.nbl_per_load = None

arithmetic.sum_diff_2_even_odd(sum_infilename=args.sumfilename,
                              diff_infilename=args.difffilename,
                              even_outfilename=args.evenfilename,
                              odd_outfilename=args.oddfilename,
                              overwrite_data_flags=args.overwrite_data_flags,
                              polarizations=args.polarizations,
                              nbl_per_load=args.nbl_per_load,
                              external_flags=args.external_flags,
                              clobber=args.clobber)
