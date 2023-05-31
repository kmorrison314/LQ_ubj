"""
LQ_Producer.py
based on HH_Producer.py
Workspace producers using coffea.
"""
import json

from coffea.hist import Hist, Bin, export1d
from coffea.processor import ProcessorABC, LazyDataFrame, dict_accumulator
from uproot3 import recreate
import numpy as np

class WSProducer(ProcessorABC):
    """
    A coffea Processor which produces a workspace.
    This applies selections and produces histograms from kinematics.
    """

    histograms = NotImplemented
    selection = NotImplemented

    def __init__(self, isMC, era=2017, sample="DY", do_syst=False, syst_var='', channel=0, weight_syst=False, haddFileName=None, flag=False, njetw=None):
        self._flag = flag
        self.do_syst = do_syst
        self.era = era
        self.isMC = isMC
        self.sample = sample
        self.channel = channel
        self.syst_var, self.syst_suffix = (syst_var, f'_sys_{syst_var}') if do_syst and syst_var else ('', '')
        self.weight_syst = weight_syst
        self._accumulator = dict_accumulator({
            name: Hist('Events', Bin(name=name, **axis))
            for name, axis in ((self.naming_schema(hist['name'], region), hist['axis'])
                               for _, hist in list(self.histograms.items())
                               for region in hist['region'])
        })
        self.outfile = haddFileName
        #print('njetw file', njetw)
        self.njet_weights = None
        if njetw is not None:
            for line in open(njetw, 'r'):
                json_read = json.loads(line)
                if json_read['year'] == era:
                    self.njet_weights = np.fromiter(json_read['weights'].values(), dtype=np.float64)
                    self.njet_weights[self.njet_weights == -999] = 1
                    self.njet_weights = np.concatenate([self.njet_weights, np.tile(self.njet_weights[-1], 20)])
                    break
                #print('NJET WEIGHTS', self.njet_weights)           
    def __repr__(self):
        return f'{self.__class__.__name__}(era: {self.era}, isMC: {self.isMC}, sample: {self.sample}, channel: {self.channel}, do_syst: {self.do_syst}, syst_var: {self.syst_var}, weight_syst: {self.weight_syst}, output: {self.outfile})'

    @property
    def accumulator(self):
        return self._accumulator

    def process(self, df, *args):
        output = self.accumulator.identity()
#revised for btagging
        #x = 0
        #df['eventcount']=x 
        weight = self.weighting(df)
        nobtag_weight = weight
        btag_weight = self.btag_weighting(df, weight)
        x = 0
        df['eventcount']=x 
#revised 06-06-22
        if self.njet_weights is not None:
            weight = self.my_btag_weighting(df, btag_weight, self.njet_weights)
        for h, hist in list(self.histograms.items()):
            for region in hist['region']:
                name = self.naming_schema(hist['name'], region)
                selec = self.passbut(df, hist['target'], region)
                if name == 'ngood_jets_btagSF':
                    output[name].fill(**{
                        'weight':btag_weight[selec],
                        name: df[hist['target']][selec]#.flatten()
                    })
                elif name == 'ngood_jets_nobtagSF':
                    output[name].fill(**{
                        'weight':nobtag_weight[selec],
                        name: df[hist['target']][selec]#.flatten()
                    })
                else:
                    output[name].fill(**{
                        'weight': weight[selec],
                        name: df[hist['target']][selec]#.flatten()
                })

        return output

    def postprocess(self, accumulator):
        return accumulator

    def passbut(self, event: LazyDataFrame, excut: str, cat: str):
        """Backwards-compatible passbut."""
        return eval('&'.join('(' + cut.format(sys=('' if self.weight_syst else self.syst_suffix)) + ')' for cut in self.selection[cat] ))#if excut not in cut))

class LQ_NTuple(WSProducer):

    zlep_bin = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 132, 146, 164, 184, 209, 239, 275, 318, 370, 432]
    eta_bin = [-5, -4, -3, -2.8, -2.4, -2, -1, 0, 1, 2, 2.4, 2.8, 3, 4, 5]
    phi_bin = [-5, -4, -3.4, -3.2, -3, -2, -1, 0, 1, 2, 3, 3.2, 3.4, 4, 5]
    met_phi = [-5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5]
    jets_bin = [0, 1, 2, 3, 4, 5]
    QCD_bin = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]
    ST_bin = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 132, 146, 164, 184, 209, 239, 275, 318, 370, 432, 500, 600, 700, 800, 900, 1000]

    histograms = {
        
#        'Nvertex':{
#            'target': 'PV_npvsGood', # name of variables from tree
#            'name'  : 'Nvertex',  # name to write to histogram
#            'region': ['signal'],
#            'axis': {'label': 'Nvertex', 'n_or_arr': 70, 'lo':0, 'hi': 70}
#        },
        'Z_cand_mass': {
            'target': 'Z_mass',
            'name'  : 'Zlep_cand_mass',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'Zlep_cand_mass', 'n_or_arr': zlep_bin}
            #'axis': {'label': 'Z mass (GeV)', 'n_or_arr': 80, 'lo':50, 'hi': 130}
        },    
        'Zlep_cand_mass_QCD_B': {
            'target': 'Z_mass',
            'name'  : 'Zlep_cand_mass_QCD_B',  # name to write to histogram
            'region': ['QCD_B'],
            'axis': {'label': 'Zlep_cand_mass', 'n_or_arr': zlep_bin}
            #'axis': {'label': 'Z mass (GeV)', 'n_or_arr': 80, 'lo':50, 'hi': 130}
        },
        'Zlep_cand_mass_QCD_C': {
            'target': 'Z_mass',
            'name'  : 'Zlep_cand_mass_QCD_C',  # name to write to histogram
            'region': ['QCD_C'],
            'axis': {'label': 'Zlep_cand_mass', 'n_or_arr': zlep_bin}
        },
        'Zlep_cand_mass_QCD_D': {
            'target': 'Z_mass',
            'name'  : 'Zlep_cand_mass_QCD_D',  # name to write to histogram
            'region': ['QCD_D'],
            'axis': {'label': 'Zlep_cand_mass', 'n_or_arr': zlep_bin}
       },
        'Zlep_cand_mass_DYcontrol': {
            'target': 'Z_mass',
            'name'  : 'Zlep_cand_mass_DYcontrol',  # name to write to histogram
            'region': ['DYcontrol'],
           #'axis': {'label': 'Zlep_cand_mass', 'n_or_arr': zlep_bin}
            'axis': {'label': 'Zlep_cand_mass', 'n_or_arr':  40, 'lo': 80, 'hi': 100}
        },
        'Zlep_cand_mass_DYcontrol_QCD_C': {
            'target': 'Z_mass',
            'name'  : 'Zlep_cand_mass_DYcontrol_QCD_C',  # name to write to histogram
            'region': ['DYcontrol_QCD_C'],
            #'axis': {'label': 'Zlep_cand_mass', 'n_or_arr': zlep_bin}
            'axis': {'label': 'Zlep_cand_mass', 'n_or_arr':  40, 'lo': 80, 'hi': 100}
        },
        'Zlep_cand_mass_TTcontrol': {
            'target': 'Z_mass',
            'name'  : 'Zlep_cand_mass_TTcontrol',  # name to write to histogram
            'region': ['TTcontrol'],
            'axis': {'label': 'Zlep_cand_mass', 'n_or_arr': zlep_bin}
            #'axis': {'label': 'Zlep_cand_mass', 'n_or_arr': 70, 'lo': 0, 'hi': 100}
        },
        'Zlep_cand_mass_TTcontrol_QCD_C': {
            'target': 'Z_mass',
            'name'  : 'Zlep_cand_mass_TTcontrol_QCD_C',  # name to write to histogram
            'region': ['TTcontrol_QCD_C'],
            'axis': {'label': 'Zlep_cand_mass', 'n_or_arr': zlep_bin}
        },
        'Zlep_cand_pt': {
            'target': 'Z_pt',
            'name'  : 'Zlep_cand_pt',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'Zlep_cand_pt', 'n_or_arr': zlep_bin}
        },  
        'Zlep_cand_eta': {
            'target': 'Z_eta',
            'name'  : 'Zlep_cand_eta',  # name to write to histogram
            'region': ['signal_btag'],
            #'axis': {'label': 'Zlep_cand_eta', 'n_or_arr': eta_bin}
            'axis': {'label': 'Zlep_cand_eta', 'n_or_arr': 190, 'lo': -9, 'hi': 9}
        }, 
        'Zlep_cand_phi': {
            'target': 'Z_phi',
            'name'  : 'Zlep_cand_phi',  # name to write to histogram
            'region': ['signal_btag'],
            #'axis': {'label': 'Zlep_cand_eta', 'n_or_arr': eta_bin}
            'axis': {'label': 'Zlep_cand_phi', 'n_or_arr': phi_bin}
        },   
        'Zlep_cand_pt_QCD_C': {
            'target': 'Z_pt',
            'name'  : 'Zlep_cand_pt_QCD_C',  # name to write to histogram
            'region': ['QCD_C'],
            'axis': {'label': 'Zlep_cand_pt', 'n_or_arr': zlep_bin}
        },  
        'Zlep_cand_eta_QCD_C': {
            'target': 'Z_eta',
            'name'  : 'Zlep_cand_eta_QCD_C',  # name to write to histogram
            'region': ['QCD_C'],
            #'axis': {'label': 'Zlep_cand_eta', 'n_or_arr': eta_bin}
            'axis': {'label': 'Zlep_cand_eta', 'n_or_arr': 190, 'lo': -9, 'hi': 9}
        },

        'Z_cand_mass': {
            'target': 'Z_mass',
            'name'  : 'Z_mass_btag2',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'Z mass (GeV)', 'n_or_arr': 80, 'lo':50, 'hi': 130}
        },
        'Z_cand_pt': {
           'target': 'Z_pt',
            'name'  : 'Z_pt_btag2',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'Z #it{p}_{T} (GeV)', 'n_or_arr': zlep_bin}
        },  
        'Z_cand_mass': {
            'target': 'Z_mass',
            'name'  : 'Z_mass_btag3',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'Z mass (GeV)', 'n_or_arr': 80, 'lo':50, 'hi': 130}
        },
        'Z_cand_pt': {
            'target': 'Z_pt',
            'name'  : 'Z_pt_btag3',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'Z #it{p}_{T} (GeV)', 'n_or_arr': zlep_bin}
        },  
        'Z_cand_mass': {
            'target': 'Z_mass',
            'name'  : 'Z_mass_btag4',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'Z mass (GeV)', 'n_or_arr': 80, 'lo':50, 'hi': 130}
        },
        'Z_cand_pt': {
            'target': 'Z_pt',
            'name'  : 'Z_pt_btag4',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'Z #it{p}_{T} (GeV)', 'n_or_arr': zlep_bin}
        },  
        #Start of editing new plots in      
	'lead_lep_pt': {
            'target': 'lead_lep_pt',
            'name'  : 'lead_lep_pt',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'lead lep #it{p}_{T} (GeV)', 'n_or_arr': zlep_bin}
        },
	'lead_lep_eta': {
            'target': 'lead_lep_eta',
            'name'  : 'lead_lep_eta',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'lead lep eta (GeV)', 'n_or_arr': eta_bin}
        },
	'lead_lep_phi': {
            'target': 'lead_lep_phi',
            'name'  : 'lead_lep_phi',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'lead lep phi (GeV)', 'n_or_arr': phi_bin}
        },
	'trail_lep_pt': {
            'target': 'trail_lep_pt',
            'name'  : 'trail_lep_pt',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'trail lep #it{p}_{T} (GeV)', 'n_or_arr': zlep_bin}
        },
        'trail_lep_eta': {
            'target': 'trail_lep_eta',
            'name'  : 'trail_lep_eta',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'trail lep eta (GeV)', 'n_or_arr': eta_bin}
        },
	'trail_lep_phi': {
            'target': 'trail_lep_phi',
            'name'  : 'trail_lep_phi',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'trail lep phi (GeV)', 'n_or_arr': phi_bin}
        },
	'lead_jet_pt': {
            'target': 'lead_jet_pt',
            'name'  : 'lead_jet_pt',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'lead jet #it{p}_{T} (GeV)', 'n_or_arr': zlep_bin}
        },
        'lead_jet_eta': {
            'target': 'lead_jet_eta',
            'name'  : 'lead_jet_eta',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'lead jet eta (GeV)', 'n_or_arr': eta_bin}
        },
        'lead_jet_phi': {
            'target': 'lead_jet_phi',
            'name'  : 'lead_jet_phi',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'lead jet phi (GeV)', 'n_or_arr': phi_bin}
        },	
	'lead_bjet_pt': {
            'target': 'lead_bjet_pt',
            'name'  : 'lead_bjet_pt',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'lead bjet #it{p}_{T} (GeV)', 'n_or_arr': zlep_bin}
        },
        'lead_bjet_eta': {
            'target': 'lead_bjet_eta',
            'name'  : 'lead_bjet_eta',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'lead bjet eta (GeV)', 'n_or_arr': eta_bin}
        },
        'lead_bjet_phi': {
            'target': 'lead_bjet_phi',
            'name'  : 'lead_bjet_phi',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'lead bjet phi (GeV)', 'n_or_arr': phi_bin}
        },
	'met_filter': {
            'target': 'met_filter',
            'name'  : 'met_filter',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'met filter (GeV)', 'n_or_arr': met_phi}
        },
	'met_phi': {
            'target': 'met_phi',
            'name'  : 'met_phi',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'met phi (GeV)', 'n_or_arr': met_phi}
        },
        'met_pt': {
            'target': 'met_pt',
            'name'  : 'met_pt',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'met #it{p}_{T} (GeV)', 'n_or_arr': zlep_bin}
        },
	'ngood_bjets': {
            'target': 'ngood_bjets',
            'name'  : 'ngood_bjets',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'N bjets', 'n_or_arr': jets_bin}
        },
    
        'Z_cand_mass': {
            'target': 'Z_mass',
            'name'  : 'Zlep_cand_mass',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'Zlep_cand_mass1', 'n_or_arr': zlep_bin}
            #'axis': {'label': 'Z mass (GeV)', 'n_or_arr': 80, 'lo':50, 'hi': 130}
        },
        'Z_cand_mass': {
            'target': 'Z_mass',
            'name'  : 'Zlep_cand_mass',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'Zlep_cand_mass', 'n_or_arr': zlep_bin}
            #'axis': {'label': 'Z mass (GeV)', 'n_or_arr': 80, 'lo':50, 'hi': 130}
        },
        'Z_cand_mass': {
            'target': 'Z_mass',
            'name'  : 'Zlep_cand_mass',  # name to write to histogram
            'region': ['signal_btag'],
           'axis': {'label': 'Zlep_cand_mass3', 'n_or_arr': zlep_bin}
            #'axis': {'label': 'Z mass (GeV)', 'n_or_arr': 80, 'lo':50, 'hi': 130}
        },



	'ngood_jets': {
            'target': 'ngood_jets',
            'name'  : 'ngood_jets',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'ngood_jets', 'n_or_arr': 21, 'lo': -0.5, 'hi': 20.5}
        },
       'ngood_jets_btagSF': {
            'target': 'ngood_jets',
            'name'  : 'ngood_jets_btagSF',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'ngood_jets', 'n_or_arr': 21, 'lo': -0.5, 'hi': 20.5}
        },
       'ngood_jets_btagSF_nobtagSF': {
            'target': 'ngood_jets',
            'name'  : 'ngood_jets_nobtagSF',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'ngood_jets', 'n_or_arr': 21, 'lo': -0.5, 'hi': 20.5}
        },

	    'QCDScale0wUp': {
            'target': 'QCDScale0wUp',
            'name'  : 'QCDScale0wUp',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'QCDScale0wUp', 'n_or_arr': QCD_bin}
        },
	    'QCDScale0wDown': {
            'target': 'QCDScale0wDown',
            'name'  : 'QCDScale0wDown',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'QCDScale0wDown', 'n_or_arr': QCD_bin}
        },
	    'QCDScale1wUp': {
            'target': 'QCDScale1wUp',
           'name'  : 'QCDScale1wUp',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'QCDScale1wUp', 'n_or_arr': QCD_bin}
        },
	    'QCDScale1wDown': {
            'target': 'QCDScale1wDown',
            'name'  : 'QCDScale1wDown',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'QCDScale1wDown', 'n_or_arr': QCD_bin}
       },
	    'QCDScale2wUp': {
            'target': 'QCDScale2wUp',
            'name'  : 'QCDScale2wUp',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'QCDScale2wUp', 'n_or_arr': QCD_bin}
        },
	    'QCDScale2wDown': {
            'target': 'QCDScale2wDown',
            'name'  : 'QCDScale2wDown',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'QCDScale2wDown', 'n_or_arr': QCD_bin}
        },
	    'jetHT': {
            'target': 'jetHT',
            'name'  : 'jetHT',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'jetHT', 'n_or_arr': zlep_bin}
        }, 
	    'ST': {
            'target': 'ST',
            'name'  : 'ST',  # name to write to histogram
            'region': ['signal_btag'],
            'axis': {'label': 'ST', 'n_or_arr': ST_bin}
        },      
    }
    selection = {
            "signal_btag" : [
                "event.lep_category    == self.channel", ## 1 = dimuons, 2 = dielectrons
                "event.event_category    == 1", ## 2= OS leptons, 1= SS leptons
                "event.lead_jet_pt > 50",
                "event.lead_lep_pt  > 50",
                #"event.trail_jet_pt > 20"
                "event.trail_lep_pt > 30",
		"event.lead_lep_eta < 2.4",
		"event.lead_jet_eta < 2.4",
                "event.met_filter == 1 ",
                "event.ngood_jets >= 1",
                "event.ngood_bjets >= 0",
                #"event.Z_pt < 100",
	        	#changed from 0,1,2
	        	#"event.met_pt > 100",
	        	#mass(mumu)
                "event.Z_mass > 15",
                #"event.Z_mass < 100",
                #"event.met_pt < 93",
            ],
            "QCD_B" : [
                "event.lep_category    == self.channel", ## 1 = dimuons, 2 = dielectrons
                "event.event_category    == 2", ## 2= OS leptons, 1= SS leptons
                #"event.lead_jet_pt > 20",
                #"event.lead_lep_pt  > 25",
                #"event.trail_jet_pt > 20"
                #"event.trail_lep_pt > 15",
		"event.lead_lep_pt > 50",
		"event.lead_jet_pt > 50",
		"event.trail_lep_pt > 30",
		"event.lead_lep_eta < 2.4",
		"event.lead_jet_eta < 2.4",
                "event.met_filter == 1 ",
                "event.ngood_jets >= 1",
                "event.ngood_bjets >= 0",
                "event.Z_mass > 15",
                #"event.Z_mass < 100",
                #"event.met_pt < 93",
                #"event.Z_pt < 100",
            ],
            "QCD_C" : [
                "event.lep_category    == self.channel", ## 1 = dimuons, 2 = dielectrons
                "event.event_category    == 3", ## 2= OS leptons, 1= SS leptons
                #"event.lead_jet_pt > 20",
                #"event.lead_lep_pt  > 25",
                #"event.trail_jet_pt > 20"
                #"event.trail_lep_pt > 15",
		"event.lead_lep_pt > 50",
		"event.lead_jet_pt > 50",
		"event.trail_lep_pt > 30",
		"event.lead_lep_eta < 2.4",
		"event.lead_jet_eta < 2.4",
                "event.met_filter == 1 ",
                #"event.met_pt < 75 ",
                "event.ngood_jets >= 1",
                "event.ngood_bjets >= 0",
                "event.Z_mass > 15",
                #"event.Z_mass < 100",
                #"event.met_pt < 93",
                #"event.Z_pt < 100",
            ],
            "QCD_D" : [
                "event.lep_category    == self.channel", ## 1 = dimuons, 2 = dielectrons
                "event.event_category    == 4", ## 2= OS leptons, 1= SS leptons
                #"event.lead_jet_pt > 20",
                #"event.lead_lep_pt  > 25",
                #"event.trail_jet_pt > 20"
                #"event.trail_lep_pt > 15",
		"event.lead_lep_pt > 50",
		"event.lead_jet_pt > 50",
		"event.trail_lep_pt > 30",
		"event.lead_lep_eta < 2.4",
		"event.lead_jet_eta < 2.4",
		"event.trail_lep_eta < 2.4",
                "event.met_filter == 1 ",
                "event.ngood_jets >= 1",
                "event.ngood_bjets >= 0",
                "event.Z_mass > 15",
                #"event.Z_mass < 100",
                #"event.met_pt < 93",
                #"event.Z_pt < 100",
            ],
            "DYcontrol" : [
                "event.lep_category == self.channel", ## 1 = dimuons, 2 = dielectrons
                "event.event_category == 1", ## 2= OS leptons, 1= SS leptons
                "event.met_filter == 1 ",
		"event.lead_lep_pt > 50",
                "event.lead_jet_pt > 50",
                "event.trail_lep_pt > 30",
                "event.lead_lep_eta < 2.4",
                "event.lead_jet_eta < 2.4",
                "event.trail_lep_eta < 2.4",
                "event.ngood_jets > 1",
                "event.ngood_bjets > 0",
                "event.Z_mass > 80",
                "event.Z_mass < 100",
                #"event.met_pt < 100",
            ],
            "DYcontrol_QCD_C" : [
                "event.lep_category == self.channel", ## 1 = dimuons, 2 = dielectrons
                "event.event_category == 3", ## 2= OS leptons, 1= SS leptons
                "event.met_filter == 1 ",
		"event.lead_lep_pt > 50",
                "event.lead_jet_pt > 50",
                "event.trail_lep_pt > 30",
                "event.lead_lep_eta < 2.4",
                "event.lead_jet_eta < 2.4",
                "event.trail_lep_eta < 2.4",
                "event.ngood_jets > 1",
                "event.ngood_bjets > 0",
                "event.Z_mass > 80",
                "event.Z_mass < 100",
                #"event.met_pt < 100",
            ],
            "TTcontrol" : [
                "event.lep_category == self.channel", ## 1 = dimuons, 2 = dielectrons
                "event.event_category == 1", ## 2= OS leptons, 1= SS leptons
                "event.met_filter == 1 ",
		"event.lead_lep_pt > 50",
                "event.lead_jet_pt > 50",
                "event.trail_lep_pt > 30",
                "event.lead_lep_eta < 2.4",
                "event.lead_jet_eta < 2.4",
                "event.trail_lep_eta < 2.4",
                "event.ngood_jets > 1",
                "event.ngood_bjets > 1",
                "event.Z_mass > 100",
                "event.met_pt > 100",
            ],
            "TTcontrol_QCD_C" : [
                "event.lep_category == self.channel", ## 1 = dimuons, 2 = dielectrons
                "event.event_category == 3", ## 2= OS leptons, 1= SS leptons
                "event.met_filter == 1 ",
		"event.lead_lep_pt > 50",
                "event.lead_jet_pt > 50",
                "event.trail_lep_pt > 30",
                "event.lead_lep_eta < 2.4",
                "event.lead_jet_eta < 2.4",
                "event.trail_lep_eta < 2.4",
                "event.ngood_jets > 1",
                "event.ngood_bjets > 1",
                "event.Z_mass > 100",
                "event.met_pt > 100",
            ],
#            "signal" : [
#                "event.lep_category    == self.channel",
#                "event.event_category    == 1", #was 2
#                "event.met_filter == 1 ",
#                "event.ngood_jets > 0",
#                "event.Z_mass > 15",
#                "event.Z_mass < 100",
#           ],
#           "signal1" : [
#                "event.lep_category    == self.channel",
#                "event.event_category    == 2",
#                "event.met_filter == 1 ",
#                "event.ngood_jets > 0",
#                "event.Z_mass > 15",
#                "event.Z_mass < 100",
#           ],
#           "signal2" : [
#                "event.lep_category    == self.channel",
#                "event.event_category    == 2",
#                "event.met_filter == 1 ",
#                "event.ngood_jets > 0",
#                "event.Z_mass > 100",
#           ],
#           "signal3" : [
#                "event.lep_category    == self.channel",
#                "event.event_category    == 2",
#                "event.met_filter == 1 ",
#                "event.ngood_jets == 1",
#                "event.met_pt > 100",
#                "event.Z_mass > 100",
#           ],
#           "signal4" : [
#                "event.lep_category    == self.channel",
#                "event.event_category    == 1",
#                "event.met_filter == 1 ",
#                "event.ngood_jets > 0",
#                #"event.met_pt > 100",
#                "event.Z_mass > 15",
#                "event.Z_mass < 100",
#           ],
#           "signal5" : [
#                "event.lep_category    == self.channel",
#                "event.event_category    == 1",
#                "event.met_filter == 1 ",
#                "event.ngood_jets > 0",
#                #"event.met_pt > 100",
#                "event.Z_mass > 15",
#                "event.Z_mass < 100",
#           ],
    }
#Signal MET_filter use to be 2

    def weighting(self, event: LazyDataFrame):
        weight = 1.0
        try:
            weight = event.xsecscale
        except:
            return "ERROR: weight branch doesn't exist"

        if self.isMC:
            try:
                if "puWeight" in self.syst_suffix:
                    if "Up" in self.syst_suffix:
                        weight = weight * event.puWeightUp
                    else:
                        weight = weight * event.puWeightDown
                else:
                    weight = weight * event.puWeight
            except:
                pass

            #L1PreFiringWeight
            try:
                if "L1PreFiringWeight" in self.syst_suffix:
                    if "Up" in self.syst_suffix:
                        weight = weight * event.L1PreFiringWeight_Up
                    else:
                        weight = weight * event.L1PrefireWeight_Dn
                else:
                    weight = weight * event.L1PrefireWeight
            except:
                pass

            #MuonRecoSF
            try:
                if "MuonRecoSF" in self.syst_suffix:
                    if "Up" in self.syst_suffix:
                        weight = weight * event.MuonRecoSF_Up
                    else:
                        weight = weight * event.MuonRecoSF_Down
                else:
                    weight = weight * event.MuonRecoSF
            except:
                pass

            # PDF uncertainty
            if "PDF" in self.syst_suffix:
                try:
                    if "Up" in self.syst_suffix:
                        weight = weight * event.pdfw_Up
                    else:
                        weight = weight * event.pdfw_Down
                except:
                    pass

            #Muon SF
            if "MuonSF" in self.syst_suffix:
                if "Up" in self.syst_suffix:
                    weight = weight * event.w_muon_SFUp
                else:
                    weight = weight * event.w_muon_SFDown
            else:
                weight = weight * event.w_muon_SF

            # Electron SF # we dont have these guys yet
#            if "ElecronSF" in self.syst_suffix:
#                if "Up" in self.syst_suffix:
#                    weight = weight * event.w_electron_SFUp
#                else:
#                    weight = weight * event.w_electron_SFDown
#            else:
#                weight = weight * event.w_electron_SF

            #Prefire Weight
            try:
                if "Prefire" in self.syst_suffix:
                    if "Up" in self.syst_suffix:
                        weight = weight * event.Prefire_Up
                    else:
                        weight = weight * event.Prefire_Down
                else:
                    weight = weight * event.Prefire
            except:
                pass

            #TriggerSFWeight
            try:
                if "TriggerSF" in self.syst_suffix:
                    if "Up" in self.syst_suffix:
                       weight = weight * event.TriggerSFUp
                    else:
                       weight = weight * event.TriggerSFDown
                else:
                    weight = weight * event.TriggerSF
            except:
                pass
        return weight

    def btag_weighting(self, event: LazyDataFrame, weight):
        try:
            if self.isMC:
                 weight = weight * event.w_btag_SF
        except:
            pass

        return weight

    def my_btag_weighting(self, event: LazyDataFrame, weight, njet_weights):
        try:
            if self.isMC:
                 weight = weight * njet_weights[event.ngood_jets]
        except:
            pass

        return weight

    def naming_schema(self, name, region):
        return f'{name}{self.syst_suffix}'
