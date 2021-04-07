#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2020 the HERA Project
# Licensed under the MIT License

"""Command-line drive script for hera_cal.xtalk_filter with baseline parallelization. Only performs DAYENU Filtering"""

from hera_cal import frf
import sys
import hera_cal.io as io

parser = frf.tophat_frfilter_argparser()

ap = parser.parse_args()

# set kwargs
if ap.mode == 'clean':
    filter_kwargs = {'window': ap.window,
                    'maxiter': ap.maxiter, 'edgecut_hi': ap.edgecut_hi,
                    'edgecut_low': ap.edgecut_low, 'gain': ap.gain}
    if ap.window == 'tukey':
        filter_kwargs['alpha'] = ap.alpha
    avg_red_bllens = False
    skip_gaps_larger_then_filter_period = False
    skip_flagged_edges = False
    max_contiguous_edge_flags = 10000
    flag_model_rms_outliers = False
elif ap.mode == 'dayenu':
    filter_kwargs = {}
    avg_red_bllens = True
    max_contiguous_edge_flags = 10000
    skip_gaps_larger_then_filter_period = False
    skip_flagged_edges = False
    flag_model_rms_outliers = False
elif ap.mode == 'dpss_leastsq':
    filter_kwargs = {}
    avg_red_bllens = True
    skip_gaps_larger_then_filter_period=True
    skip_flagged_edges = True
    max_contiguous_edge_flags = 1
    flag_model_rms_outliers = True


if args.cornerturnfile is not None:
    baseline_list = io.baselines_from_filelist_position(filename=ap.cornerturnfile, filelist=ap.datafilelist)
else:
    baseline_list = None

if len(baseline_list) > 0:
    # modify output file name to include index.
    spw_range = ap.spw_range
    # allow none string to be passed through to ap.calfile
    if isinstance(ap.calfile_list, str) and ap.calfile_list.lower() == 'none':
        ap.calfile_list = None
    # Run Xtalk Filter
    frf.load_tophat_frfilter_and_write(ap.datafilelist, calfile_list=ap.calfilelist, avg_red_bllens=True,
                                       baseline_list=baseline_list, spw_range=ap.spw_range,
                                       cache_dir=ap.cache_dir, filled_outfilename=ap.filled_outfilename,
                                       clobber=ap.clobber, write_cache=ap.write_cache, CLEAN_outfilename=ap.CLEAN_outfilename,
                                       read_cache=ap.read_cache, mode=ap.mode, res_outfilename=ap.res_outfilename,
                                       factorize_flags=ap.factorize_flags, time_thresh=ap.time_thresh,
                                       max_contiguous_edge_flags=ap.max_contiguous_edge_flags,
                                       add_to_history=' '.join(sys.argv), verbose=ap.verbose,
                                       skip_flagged_edges=ap.skip_flagged_edges,
                                       flag_yaml=ap.flag_yaml, Nbls_per_load=ap.Nbls_per_load,
                                       external_flags=ap.external_flags, inpaint=ap.inpaint, frate_standoff=ap.frate_standoff,
                                       skip_contiguous_flags=skip_gaps_larger_then_filter_period,
                                       overwrite_flags=ap.overwrite_flags, skip_if_flag_within_edge_distance=ap.skip_if_flag_within_edge_distance,
                                       flag_model_rms_outliers=flag_model_rms_outliers,
                                       tol=ap.tol, skip_wgt=ap.skip_wgt, max_frate_coeffs=ap.max_frate_coeffs,
                                       frac_frate_sky_max=ap.frac_frate_sky_max, frate_standoff=ap.frate_standoff, min_frate=ap.min_frate,
                                       clean_flags_in_resid_flags=True, **filter_kwargs)
