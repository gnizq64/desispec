#
# See top-level LICENSE.rst file for Copyright information
#
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

from collections import OrderedDict

from ..defs import (task_name_sep, task_state_to_int, task_int_to_state)

from ...util import option_list

from ...io import findfile

from .base import BaseTask

import sys,re,os,copy

# NOTE: only one class in this file should have a name that starts with "Task".

class TaskExtract(BaseTask):
    """Class containing the properties of one extraction task.
    """
    def __init__(self):
        super(TaskExtract, self).__init__()
        # then put int the specifics of this class
        # _cols must have a state
        self._type = "extract"
        self._cols = [
            "night",
            "band",
            "spec",
            "expid",
            "state"
        ]
        self._coltypes = [
            "integer",
            "text",
            "integer",
            "integer",
            "integer"
        ]
        # _name_fields must also be in _cols
        self._name_fields  = ["night","band","spec","expid"]
        self._name_formats = ["08d","s","d","08d"]
        
    def _paths(self, name):
        """See BaseTask.paths.
        """
        props = self.name_split(name)
        camera = "{}{}".format(props["band"], props["spec"])
        return [ findfile("frame", night=props["night"], expid=props["expid"],
            camera=camera, groupname=None, nside=None, band=props["band"],
            spectrograph=props["spec"]) ]

    def _deps(self, name, db, inputs):
        """See BaseTask.deps.
        """
        from .base import task_classes
        props = self.name_split(name)
        deptasks = {
            "input" : task_classes["pix"].name_join(props),
            "fibermap" : task_classes["fibermap"].name_join(props),
            "psf" : task_classes["psfnight"].name_join(props)
            }
        return deptasks
    
    def _run_max_procs(self, procs_per_node):
        """See BaseTask.run_max_procs.
        """
        return 20 # 20 bundles per camera


    def _run_time(self, name, procs_per_node, db=None):
        """See BaseTask.run_time.
        """
        return 15 # 8 minute per bundle of 25 fibers on edison, but can be slower


    def _run_defaults(self):
        """See BaseTask.run_defaults.
        """
        opts = {}
        opts["regularize"] = 0.0
        opts["nwavestep"] = 50
        opts["verbose"] = False
        opts["wavelength_b"] = "3579.0,5939.0,0.8"
        opts["wavelength_r"] = "5635.0,7731.0,0.8"
        opts["wavelength_z"] = "7445.0,9824.0,0.8"
        return opts


    def _option_list(self, name, opts):
        """Build the full list of options.

        This includes appending the filenames and incorporating runtime
        options.
        """
        from .base import task_classes, task_type

        deps = self.deps(name)
        options = {}
        options["input"]    = task_classes["pix"].paths(deps["input"])[0]
        options["fibermap"] = task_classes["fibermap"].paths(deps["fibermap"])[0]
        options["psf"]      = task_classes["psfnight"].paths(deps["psf"])[0]
        options["output"]   = self.paths(name)[0]

        # extract the wavelength range from the options, depending on the band
        props = self.name_split(name)
        optscopy = copy.deepcopy(opts)
        wkey = "wavelength_{}".format(props["band"])
        wave = optscopy[wkey]
        del optscopy["wavelength_b"]
        del optscopy["wavelength_r"]
        del optscopy["wavelength_z"]
        optscopy["wavelength"] = wave

        options.update(optscopy)
        return option_list(options)

    def _run_cli(self, name, opts, procs, db=None):
        """See BaseTask.run_cli.
        """
        entry = "desi_extract_spectra"
        optlist = self._option_list(name, opts)
        com = "{} {}".format(entry, " ".join(optlist))
        return com

    def _run(self, name, opts, comm, db=None):
        """See BaseTask.run.
        """
        from ...scripts import extract
        optlist = self._option_list(name, opts)
        args = extract.parse(optlist)
        if comm is None :
            extract.main(args)
        else :
            extract.main_mpi(args, comm=comm)
        return
