# -*- coding: utf-8 -*-

# from fflip.omm.util import filter_solution
import numpy as np
# import pandas as pd
import nlopt
# from fflip.ljpme.util import get_sign, rename_row_col
# from fflip.ljpme.modelcomp import ModelCompound
from fflip.ljpme.optimizers import Optimizer


class MixedOptimizer(Optimizer):
    """
    An NLOPT optimizer targets model compounds' QM and membrane experiments.
    """

    def __init__(self, model_compounds, qme, crd_files, mc_parameters,
                 parameters, target_properties, special_properties,
                 uncertainty_scaling, toppar_files):
        """

        Args:
            model_compounds（dict): model compounds, names as keys.
            qme (dict): QM energies of model compounds, names as keys.
            crd_files (dict): crd files in the same order as the QM energies, names as keys
            mc_parameters (dict): lists of DrudeParameter (fflip.omm)
            following the atom naming of model compounds
            parameters (list): a list of DrudeParameter (fflip.omm),
            following the atom naming of the lipid molecule

        """
        super().__init__(
            target_properties, special_properties, model_compounds,
            uncertainty_scaling, parameters=parameters
        )
        self.mc_parameters = mc_parameters
        self.crd_files = crd_files
        self.qme = dict()
        for mc in qme:
            self.qme[mc] = qme[mc] - qme[mc].min()
        self.paramters = parameters
        self.target_properties = target_properties
        self.special_properties = special_properties
        self.toppar_files = toppar_files

    def obj_func(self, x, grad):
        self.X = x
        sqrt_ssr_dict = dict()
        for mc in self.model_compounds:
            # glyp = ModelCompound(
            #     mc,
            #     psf_file='/u/alanyu/drude/structure_bank/psf_files/model/glyp.psf',
            #     ff='drude'
            # )
            # self.toppar_files = glob.glob('toppar/*')
            self.model_compounds[mc].load_parameter_files(self.toppar_files)
            self.model_compounds[mc].load_nbthole(self.mc_parameters[mc], x)
            self.model_compounds[mc].generate_gas_system()
            self.model_compounds[mc].change_nb_params(self.mc_parameters[mc], x)
            self.model_compounds[mc].generate_context()

            omm_e = self.model_compounds[mc].generate_energies(
                self.crd_files[mc]
            )
            omm_e = omm_e - omm_e.min()
            w = np.exp(-1.0 * omm_e / (0.001987 * 303.15)) + \
                np.exp(-1.0 * self.qme[mc] / (0.001987 * 303.15))
            sqrt_ssr = np.sqrt(np.sum(w * (omm_e - self.qme[mc]) ** 2))
            sqrt_ssr_dict[mc] = sqrt_ssr
        self.gen_target_vector()
        target_vector = list(self.T) + [0 for mc in self.model_compound_names]
        product1 = np.matmul(self.W, self.S)
        product2 = np.matmul(product1, list(x) + [sqrt_ssr_dict[mc] for mc in self.model_compound_names])
        self.D = product2
        diff = product2 - np.matmul(self.W, target_vector)
        ssr = np.sum(diff**2)
        ssr_p1 = np.sum(diff[:self.num_all_properties]**2)
        ssr_p2 = np.sum(diff[self.num_all_properties: self.num_all_properties + self.num_qmc]**2)
        ssr_p3 = np.sum(diff[
            self.num_all_properties + self.num_qmc: self.num_all_properties + self.num_qmc + self.num_parameters
        ]**2)
        ssr_p4 = np.sum(diff[
            self.num_all_properties + self.num_qmc + self.num_parameters:
            self.num_all_properties + self.num_qmc + self.num_parameters + self.num_model_compounds
        ]**2)
        if self.counter % self.print_interval == 0:
            if self.counter == 0:
                print("        ssr_properties    ssr_qm_charge  ssr_regularization    ssr_qm_torsion     ssr_sum")
            print('Iteration {}: {} {} {} {} {}...'.format(self.counter, ssr_p1, ssr_p2, ssr_p3, ssr_p4, ssr))
        self.counter += 1
        return ssr

    def __call__(self, method, print_interval, hard_bounds, drop_bounds,
                 forbid, qmscan_weights, qmc_weight=0, **options):
        self.print_interval = print_interval
        self.counter = 0
        dimension = len(self.parameters)
        self.hard_bounds = hard_bounds
        self.drop_bounds = drop_bounds
        self.forbid = forbid
        self.qmscan_weights = qmscan_weights
        self.qmc_weight = qmc_weight
        self.gen_weight_matrix(
            self.hard_bounds, self.drop_bounds, forbid=self.forbid,
            qmc_weight=self.qmc_weight, qmscan_weights=self.qmscan_weights,
            verbose=0
        )
        self.gen_sensitivity_matrix(scale=1)
        opt = nlopt.opt(method, dimension)
        self.optimizer = opt
        if "lower_bounds" in options:
            opt.set_lower_bounds(options["lower_bounds"])
        if "upper_bounds" in options:
            opt.set_upper_bounds(options["upper_bounds"])
        if "maxiter" in options:
            opt.set_maxeval(options["maxiter"])
        opt.set_min_objective(self.obj_func)
        if "xtol_rel" in options:
            opt.set_xtol_rel(options["xtol_rel"])
        else:
            opt.set_xtol_rel(0.002)
        # TODO: could use random start instead
        x0 = np.zeros(len(self.parameters))
        x = opt.optimize(x0)
        # minf = opt.last_optimum_value()
        return x
