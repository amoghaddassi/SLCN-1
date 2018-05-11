import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.optimize import brute
from alien_task import Task
from alien_agents import Agent
from alien_record_data import RecordData
# from ps_task import Task
# from ps_agent import Agent
# from ps_record_data import RecordData


class FitParameters(object):
    def __init__(self, parameters, task_stuff, agent_stuff):
        self.parameters = parameters
        self.task_stuff = task_stuff
        self.agent_stuff = agent_stuff
        assert self.agent_stuff['name'] in ['alien', 'PS_']
        self.n_fit_par = sum(parameters.fit_pars)

    def get_agent_data(self, way, data_path='', all_Q_columns=False, all_params_lim=()):
        assert(way in ['simulate', 'real_data', 'interactive'])
        if way in ['simulate', 'interactive']:
            return self.simulate_agent(all_params_lim, all_Q_columns, interactive=way == 'interactive')
        elif way == 'real_data':
            file_name = data_path + '/' + self.agent_stuff['name'] + str(self.agent_stuff['id']) + '.csv'
            return pd.read_csv(file_name)

    def simulate_agent(self, all_params_lim, all_Q_columns, interactive=False):

        task = Task(self.task_stuff)
        agent = Agent(self.agent_stuff, all_params_lim, self.task_stuff)
        record_data = RecordData(agent_id=agent.id,
                                 mode='create_from_scratch',
                                 task=task)

        for trial in range(task.n_trials):
            if interactive:
                print('\n\tTRIAL {0}'.format(str(trial)))
                task.context = int(input('Context (0, 1, 2):'))
                task.alien = int(input('Alien (0, 1, 2, 3):'))
                stimulus = [task.context, task.alien]
                suggested_action = agent.select_action(stimulus)  # calculate p_actions
                if self.agent_stuff['mix_probs']:
                    print('TS.     all values:   {0}; all ps:   {1}\n'
                          'Action. comb. values: {3}; comb. ps: {4}; suggested: {2}\n'
                          '\tall values:\n{5}'.format(
                            str(np.round(agent.Q_high[task.context, :], 2)), str(np.round(agent.p_TS, 2)),
                            str(suggested_action),
                            str(np.round(agent.Q_actions, 2)), str(np.round(agent.p_actions, 2)),
                            str(np.round(agent.Q_low[:, stimulus[1], :], 2))))
                else:
                    print('TS.     Selected:  {0}, value: {1} (all values: {2}; all ps: {3})\n'
                          'Action. Suggested: {4}, value: {5} (all values: {6}; all ps: {7})'.format(
                            str(agent.TS), str(np.round(agent.Q_high[task.context, agent.TS], 2)),
                            str(np.round(agent.Q_high[task.context, :], 2)), str(np.round(agent.p_TS, 2)),
                            str(suggested_action), str(np.round(agent.Q_low[agent.TS, task.alien, suggested_action], 2)),
                            str(np.round(agent.Q_low[agent.TS, task.alien, :], 2)), str(np.round(agent.p_actions, 2))))
                action = int(input('Action (0, 1, 2):'))
            else:
                task.prepare_trial(trial)
                stimulus = task.present_stimulus(trial)
                action = agent.select_action(stimulus)
            [reward, correct] = task.produce_reward(action)
            agent.learn(stimulus, action, reward)
            if interactive:
                if self.agent_stuff['mix_probs']:
                    print('Reward: {0} ({1})\n'
                          'Q_TS.     Old: {2}, RPE: {3}, New: {4}\n'
                          'Q_action. Old: {5}, RPE: {6}, New: {7}'.format(
                            str(np.round(reward, 2)), str(correct),
                            str(np.round(agent.old_Q_high, 2)), str(np.round(agent.RPEs_high, 2)),
                            str(np.round(agent.new_Q_high, 2)),
                            str(np.round(agent.old_Q_low, 2)), str(np.round(agent.RPEs_low, 2)),
                            str(np.round(agent.new_Q_low, 2))))
                else:
                    print('Reward: {0} ({1})\n'
                          'Q_TS.     Old: {2}, RPE: {3}, New: {4}\n'
                          'Q_action. Old: {5}, RPE: {6}, New: {7}'.format(
                        str(np.round(reward, 2)), str(correct),
                        str(np.round(agent.old_Q_high[agent.TS], 2)), str(np.round(agent.RPEs_high[agent.TS], 2)),
                        str(np.round(agent.new_Q_high[agent.TS], 2)),
                        str(np.round(agent.old_Q_low[agent.TS], 2)), str(np.round(agent.RPEs_low[agent.TS], 2)),
                        str(np.round(agent.new_Q_low[agent.TS], 2))))
            record_data.add_behavior(task, stimulus, action, reward, correct, trial)
            record_data.add_decisions(agent, trial, suff='', all_Q_columns=all_Q_columns)

        record_data.add_parameters(agent, '')  # add parameters (alpha, beta, etc.) only
        return record_data.get()

    def calculate_NLL(self, params_inf, agent_data, default_pars_lim="default", goal='calculate_NLL'):

        # Combine params_inf (current guess for fitted parameters) and default_pars_lim (default parameters)
        if default_pars_lim == "default":
            default_pars_lim = self.parameters.default_pars_lim
        pars_01 = self.parameters.change_limits(default_pars_lim, 'lim_to_01')
        pars_inf = self.parameters.change_scale(pars_01, '01_to_inf')
        fit_par_idx = np.argwhere(self.parameters.fit_pars)
        pars_inf[fit_par_idx] = params_inf

        # Bring parameters into the right scale and check that there was no error in conversion
        pars_01 = self.parameters.change_scale(pars_inf, 'inf_to_01')
        pars_lim = self.parameters.change_limits(pars_01, '01_to_lim')
        # for i, par in enumerate(self.parameters.par_names):
        #     assert((np.round(pars_lim[i], 2) == np.round(default_pars_lim[i], 2)) or self.parameters.fit_pars[i])

        # Create agent with these parameters
        agent = Agent(self.agent_stuff, pars_lim, self.task_stuff)
        if goal == 'add_decisions_and_fit':
            record_data = RecordData(agent_id=agent.id,
                                     mode='add_to_existing_data',
                                     agent_data=agent_data)

        # Let the agent do the task
        n_trials = len(agent_data)
        for trial in range(n_trials):
            if self.agent_stuff['name'] == 'alien':
                context = int(agent_data['context'][trial])
                sad_alien = int(agent_data['sad_alien'][trial])
                stimulus = np.array([context, sad_alien])
                agent.select_action(stimulus)  # calculate p_actions
                action = int(agent_data['item_chosen'][trial])
            elif self.agent_stuff['name'] == 'PS_':
                stimulus = np.nan
                agent.select_action(stimulus)  # calculate p_actions
                action = int(agent_data['selected_box'][trial])
            reward = int(agent_data['reward'][trial])
            agent.learn(stimulus, action, reward)
            if goal == 'add_decisions_and_fit':
                record_data.add_decisions(agent, trial, suff='_rec')

        BIC = - 2 * agent.LL + self.n_fit_par * np.log(n_trials)
        AIC = - 2 * agent.LL + self.n_fit_par

        if goal == 'calculate_NLL':
            return -agent.LL
        elif goal == 'calculate_fit':
            return [-agent.LL, BIC, AIC]
        elif goal == 'add_decisions_and_fit':
            record_data.add_parameters(agent, self.parameters, suff='_rec')  # add parameters and fit_pars
            record_data.add_fit(-agent.LL, BIC, AIC, suff='_rec')
            return record_data.get()

    def get_optimal_pars(self, agent_data, n_iter, default_pars_lim="default"):
        # x0 = brute(func=self.calculate_NLL,
        #            ranges=self.parameters.par_hard_limits,  # should be in the form (slice(-4, 4, 0.25), slice(-4, 4, 0.25))
        #            args=agent_data,
        #            full_output=True,
        #            finish=None)  # should try! https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brute.html#scipy.optimize.brute
        # optimized_params = self.parameters.inf_to_lim(x0)
        if default_pars_lim == "default":
            default_pars_lim = self.parameters.default_pars_lim

        # Find the minimum of n_iter different start values to get fit parameters
        values = np.zeros([n_iter, self.n_fit_par + 1])
        for iter in range(n_iter):
            start_par_inf = self.parameters.create_random_params(scale='inf', get_all=False)
            minimization = minimize(self.calculate_NLL,
                                    x0=start_par_inf,
                                    args=(agent_data, default_pars_lim),
                                    method='Nelder-Mead')
            values[iter, :] = np.concatenate(([minimization.fun], minimization.x))
        minimum = values[:, 0] == min(values[:, 0])
        fit_pars_inf = values[minimum][0]
        fit_pars_inf = fit_pars_inf[1:]

        # Combine fit parameters and fixed parameters and return all
        fixed_pars_01 = self.parameters.change_limits(default_pars_lim, 'lim_to_01')
        fixed_pars_inf = self.parameters.change_scale(fixed_pars_01, '01_to_inf')
        fit_par_idx = np.argwhere(self.parameters.fit_pars)
        fixed_pars_inf[fit_par_idx] = fit_pars_inf
        fixed_pars_01 = self.parameters.change_scale(fixed_pars_inf, 'inf_to_01')
        default_pars_lim = self.parameters.change_limits(fixed_pars_01, '01_to_lim')
        return default_pars_lim

    def write_agent_data(self, agent_data, save_path, file_name=''):
        agent_data.to_csv(save_path + file_name + "_" + str(agent_data['sID'][0]) + ".csv")
