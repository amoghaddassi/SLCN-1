import numpy as np
import pandas as pd
from scipy.optimize import brute
from scipy.optimize import basinhopping
from basinhopping_specifics import MyTakeStep, MyBounds
from minimizer_heatmap import PlotMinimizerHeatmap, CollectPaths, CollectMinima
from simulate_interactive import SimulateInteractive


class FitParameters(object):
    def __init__(self, data_set, learning_style, parameters, task_stuff, comp_stuff, agent_stuff):
        self.parameters = parameters
        self.task_stuff = task_stuff
        self.comp_stuff = comp_stuff
        self.agent_stuff = agent_stuff
        self.n_fit_par = sum(parameters['fit_pars'])
        self.data_set = data_set
        self.learning_style = learning_style

    def simulate_agent(self, all_pars, agent_id, interactive=False):

        # Import the right agent and task
        if self.data_set == 'Aliens':
            from alien_task import Task
            from competition_phase import CompetitionPhase
            from alien_agents import Agent
            from alien_record_data import RecordData
        else:
            from ps_task import Task
            from ps_record_data import RecordData
            if self.learning_style == 'Bayes':
                from ps_agents import BayesAgent as Agent
            else:
                from ps_agents import RLAgent as Agent

        # Initialize task, agent, record, and interactive game
        task = Task(self.task_stuff, 4)
        agent = Agent(self.agent_stuff, all_pars, self.task_stuff)
        record_data = RecordData(mode='create_from_scratch', task=task)
        if interactive:
            sim_int = SimulateInteractive(self.data_set, agent)
        else:
            sim_int = None

        # Play the game, phase by phase, trial by trial
        if self.data_set == 'Aliens':
            self.simulate_aliens(task, agent, record_data, interactive, sim_int)
        else:
            self.simulate_PS(task, agent, record_data, interactive, sim_int)

        record_data.add_parameters(agent, agent_id)  # add parameters (alpha, beta, etc.) only
        return record_data.get()

    def calculate_NLL(self, vary_pars, agent_data, collect_paths=None, verbose=False,
                      goal='calculate_NLL', suff='_rec'):

        # Import the right agent and task
        if self.data_set == 'Aliens':
            from alien_task import Task
            from competition_phase import CompetitionPhase
            from alien_agents import Agent
            from alien_record_data import RecordData
        else:
            from ps_task import Task
            from ps_record_data import RecordData
            if self.learning_style == 'Bayes':
                from ps_agents import BayesAgent as Agent
            else:
                from ps_agents import RLAgent as Agent

        # Get agent parameters
        all_pars = self.parameters['default_pars']
        fit_par_idx = np.argwhere(self.parameters['fit_pars']).T[0]
        all_pars[fit_par_idx] = vary_pars

        # Initialize agent and record
        agent = Agent(self.agent_stuff, all_pars, self.task_stuff)
        if goal == 'add_decisions_and_fit':
            record_data = RecordData(mode='add_to_existing_data',
                                     agent_data=agent_data)

        # Let the agent do the task
        n_trials = len(agent_data)
        for trial in range(n_trials):
            if 'Alien' in self.agent_stuff['name']:
                agent.task_phase = '1InitialLearning'
                context = int(agent_data['context'][trial])
                sad_alien = int(agent_data['sad_alien'][trial])
                stimulus = np.array([context, sad_alien])
                agent.select_action(stimulus)  # calculate p_actions
                action = int(float(agent_data['item_chosen'][trial]))
                reward = int(agent_data['reward'][trial])
                agent.learn(stimulus, action, reward)
            elif 'PS' in self.agent_stuff['name']:
                agent.select_action()  # calculate p_actions
                action = int(agent_data['selected_box'][trial])
                reward = int(agent_data['reward'][trial])
                agent.learn(action, reward)
            if goal == 'add_decisions_and_fit':
                record_data.add_decisions(agent, trial, suff=suff)

        # Calculate fit of this set of parameters
        BIC = - 2 * agent.LL + self.n_fit_par * np.log(n_trials)
        AIC = - 2 * agent.LL + self.n_fit_par

        if goal == 'calculate_NLL':
            if verbose:
                print(-agent.LL, vary_pars)
            if collect_paths:
                collect_paths.add_point(np.array(vary_pars))
            return -agent.LL
        elif goal == 'calculate_fit':
            return [-agent.LL, BIC, AIC]
        elif goal == 'add_decisions_and_fit':
            record_data.add_parameters(agent, None, self.parameters, suff=suff)  # add parameters and fit_pars
            record_data.add_fit(-agent.LL, BIC, AIC, suff=suff)
            return record_data.get()

    def get_optimal_pars(self, agent_data, minimizer_stuff, heatmap_data_path):

        if minimizer_stuff['save_plot_data']:
            plot_heatmap = PlotMinimizerHeatmap(heatmap_data_path)
            hoppin_paths = CollectPaths(colnames=self.parameters['fit_par_names'])
            fit_par_idx = np.argwhere(self.parameters['fit_pars']).T[0]
            brute_results = brute(func=self.calculate_NLL,
                                  ranges=([self.parameters['par_hard_limits'][i] for i in fit_par_idx]),
                                  args=(agent_data, hoppin_paths, minimizer_stuff['verbose']),
                                  Ns=minimizer_stuff['brute_Ns'],
                                  full_output=True,
                                  finish=None,
                                  disp=True)
            print('Finished brute!')
            plot_heatmap.pickle_brute_results(brute_results)
            hoppin_minima = CollectMinima(colnames=self.parameters['fit_par_names'])
            hoppin_paths = CollectPaths(colnames=self.parameters['fit_par_names'])  # reinitialize
        else:
            hoppin_minima = None
            hoppin_paths = None

        n_free_pars = np.sum(self.parameters['fit_pars'])
        bounds = MyBounds(xmax=np.ones(n_free_pars), xmin=np.zeros(n_free_pars))
        takestep = MyTakeStep(stepsize=minimizer_stuff['hoppin_stepsize'],
                              bounds=self.parameters['par_hard_limits'][0])
        hoppin_results = basinhopping(func=self.calculate_NLL,
                                      x0=.5 * np.ones(n_free_pars),
                                      niter=minimizer_stuff['NM_niter'],
                                      T=minimizer_stuff['hoppin_T'],
                                      minimizer_kwargs={'method': 'Nelder-Mead',
                                                        'args': (agent_data, hoppin_paths, minimizer_stuff['verbose']),
                                                        'options': {'xatol': minimizer_stuff['NM_xatol'],
                                                                    'fatol': minimizer_stuff['NM_fatol'],
                                                                    'maxfev': minimizer_stuff['NM_maxfev']}},
                                      take_step=takestep,
                                      accept_test=bounds,
                                      callback=hoppin_minima,
                                      disp=True)
        hoppin_fit_par, hoppin_NLL = [hoppin_results.x, hoppin_results.fun]

        if minimizer_stuff['save_plot_data']:
            fin_res = np.append(hoppin_fit_par, hoppin_NLL) * np.ones((1, len(hoppin_fit_par)+1))
            final_result = pd.DataFrame(fin_res, columns=self.parameters['fit_par_names'] + ['NLL'])
            final_result.to_csv(plot_heatmap.get_save_path() + 'hoppin_result.csv')
            hoppin_paths.get().to_csv(plot_heatmap.get_save_path() + 'hoppin_paths.csv')
            hoppin_minima.get().to_csv(plot_heatmap.get_save_path() + 'hoppin_minima.csv')

        print("Finished basin hopping with values {0}, NLL {1}."
              .format(np.round(hoppin_fit_par, 3), np.round(hoppin_NLL, 3)))

        # Combine fit parameters and fixed parameters and return all
        fit_par_idx = np.argwhere(self.parameters['fit_pars']).T[0]
        minimized_pars = self.parameters['default_pars']
        minimized_pars[fit_par_idx] = hoppin_fit_par
        return minimized_pars

    @staticmethod
    def simulate_PS(task, agent, record_data, interactive, sim_int):
        for trial in range(task.n_trials):

            # Select action and receive reward
            task.prepare_trial()
            if interactive:
                sim_int.trial(trial)
                sim_int.print_values_pre()
                action = int(input('Action (0, 1):'))
            else:
                action = agent.select_action()
            [reward, correct] = task.produce_reward(action)

            # Update values
            agent.learn(action, reward)
            if interactive:
                sim_int.print_values_post(action, reward, correct)

            # Save trial data
            record_data.add_behavior(action, reward, correct, task.correct_box, trial)
            record_data.add_decisions(agent, trial)

    @staticmethod
    def simulate_aliens(task, agent, record_data, interactive, sim_int):
        total_trials = 0
        for phase in ['1InitialLearning', '2CloudySeason', 'Refresher2']:
            task.set_phase(phase)
            agent.task_phase = phase
            n_trials = int(task.n_trials_per_phase[np.array(task.phases) == task.phase])
            agent.prev_context = 99
            for trial in range(n_trials):
                if interactive:
                    stimulus = sim_int.trial(trial)
                    [task.context, task.alien] = stimulus
                    sim_int.print_values_pre()
                    action = int(input('Action (0, 1, 2):'))
                else:
                    task.prepare_trial(trial)
                    stimulus = task.present_stimulus(trial)
                    action = agent.select_action(stimulus)
                [reward, correct] = task.produce_reward(action)
                agent.learn(stimulus, action, reward)
                if interactive:
                    sim_int.print_values_post(action, reward, correct)
                record_data.add_behavior(stimulus, action, reward, correct, total_trials, phase)
                record_data.add_decisions(agent, total_trials, suff='')
                total_trials += 1

        # task.set_phase('3PickAliens')
        # comp = CompetitionPhase(self.comp_stuff, self.task_stuff)
        # for trial in range(sum(comp.n_trials)):
        #     comp.prepare_trial(trial)
        #     stimuli = comp.present_stimulus(trial)
        #     selected = agent.competition_selection(stimuli, comp.current_phase)
        #     if interactive:
        #         print('\tTRIAL {0} ({1}),\nstimuli {2}, values: {3}, probs.: {4}'.format(
        #         trial, comp.current_phase, stimuli, str(np.round(agent.Q_stimuli, 2)), str(np.round(agent.p_stimuli, 2))))
        #     record_data.add_behavior_and_decisions_comp(stimuli, selected, agent.Q_stimuli, agent.p_stimuli,
        #                                                 total_trials, task.phase, comp.current_phase)
        #     total_trials += 1
        #
        # for phase in ['Refresher3', '5RainbowSeason']:
        #     task.set_phase(phase)
        #     agent.task_phase = phase
        #     n_trials = int(task.n_trials_per_phase[np.array(task.phases) == task.phase])
        #     for trial in range(n_trials):
        #         if interactive:
        #             stimulus = sim_int.trial(trial)
        #             [task.context, task.alien] = stimulus
        #             sim_int.print_values_pre()
        #             action = int(input('Action (0, 1, 2):'))
        #         else:
        #             task.prepare_trial(trial)
        #             stimulus = task.present_stimulus(trial)
        #             action = agent.select_action(stimulus)
        #         [reward, correct] = task.produce_reward(action)
        #         agent.learn(stimulus, action, reward)
        #         if interactive:
        #             sim_int.print_values_post(action, reward, correct)
        #         record_data.add_behavior(task, stimulus, action, reward, correct, total_trials, phase)
        #         record_data.add_decisions(agent, total_trials, suff='', all_Q_columns=False)
        #         total_trials += 1
