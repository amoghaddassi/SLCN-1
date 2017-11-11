import numpy as np
from model_fitting import ModelFitting
from transform_pars import TransformPars


n_agents = 50
n_iter = 10
task_stuff = {'n_actions': 2,
              'p_reward': 0.75,
              'path': 'C:/Users/maria/MEGAsync/SLCN/ProbabilisticSwitching/Prerandomized sequences'}
trans = TransformPars()

# Generate and recover
n_par = 5
agent_stuff = {'free_par': np.full(n_par, False, dtype=bool),   # which parameters are fitted (T) and fixed (F)?
               'default_par': [-10, -5, -10, -10, -10],  # parameter values if fixed (after transform: 0, 0.13, 0, 0, 0)
               'n_agents': 1}  # number of simulated agents

for learning_style in ['RL', 'Bayes']:

    agent_stuff['learning_style'] = learning_style
    if learning_style == 'Bayes':
        agent_stuff['free_par'][0] = False  # alpha
    else:
        agent_stuff['free_par'][0] = True  # alpha

    for method in ['direct', 'softmax', 'epsilon-greedy']:
        if method == 'epsilon-greedy':
            agent_stuff['free_par'][1:3] = [False, True]  # beta, epsilon
        elif method == 'softmax':
            agent_stuff['free_par'][1:3] = [True, False]  # beta, epsilon
        elif method == 'direct':
            agent_stuff['free_par'][1:3] = [False, False]  # beta, epsilon
        agent_stuff['method'] = method
        agent_stuff['data_path'] = 'C:/Users/maria/MEGAsync/SLCNdata/' + agent_stuff['learning_style'] +\
                                   '/' + agent_stuff['method'] + '_few_params'
        print('Learning:', learning_style, '\nMethod:', method)

        # Generate
        model = ModelFitting(agent_stuff, task_stuff)
        n_fit_par = sum(agent_stuff['free_par'])
        for ag in range(n_agents):
            print('agent', ag)
            rand_par = -np.log(1 / np.random.rand(n_fit_par) - 1)  # inverse sigmoid -> make 0 to 1 into -inf to inf
            sim_par = model.simulate_agents(ag, rand_par)
            print('sim_par', sim_par)

        # Recover
            best_par = model.minimize_NLL(ag, n_fit_par, n_iter=n_iter)
            fit_par = trans.get_pars(agent_stuff, best_par)
            trans_par = trans.transform_pars(fit_par)
            print('trans_par', trans_par)
            NLL, BIC, AIC = model.calculate_fit(trans_par, ag, False)
            model.update_genrec_and_save(np.concatenate(([ag, learning_style, method, NLL, BIC, AIC], sim_par, trans_par)),
                                         agent_stuff['data_path'] + '/genrec.csv')

        # Generate and recover
        n_par = 5
        agent_stuff = {'free_par': np.full(n_par, True, dtype=bool),  # which parameters are fitted (T) and fixed (F)?
                       'default_par': [-10, -5, -10, -10, -10],
                       # parameter values if fixed (after transform: 0, 0.13, 0, 0, 0)
                       'n_agents': 1}  # number of simulated agents

for learning_style in ['RL', 'Bayes']:

    agent_stuff['learning_style'] = learning_style
    if learning_style == 'Bayes':
        agent_stuff['free_par'][0] = False  # alpha
    else:
        agent_stuff['free_par'][0] = True  # alpha

    for method in ['direct', 'softmax', 'epsilon-greedy']:
        if method == 'epsilon-greedy':
            agent_stuff['free_par'][1:3] = [False, True]  # beta, epsilon
        elif method == 'softmax':
            agent_stuff['free_par'][1:3] = [True, False]  # beta, epsilon
        elif method == 'direct':
            agent_stuff['free_par'][1:3] = [False, False]  # beta, epsilon
        agent_stuff['method'] = method
        agent_stuff['data_path'] = 'C:/Users/maria/MEGAsync/SLCNdata/' + agent_stuff['learning_style'] + \
                                   '/' + agent_stuff['method'] + '_all_params'
        print('Learning:', learning_style, '\nMethod:', method)

        # Generate
        model = ModelFitting(agent_stuff, task_stuff)
        n_fit_par = sum(agent_stuff['free_par'])
        for ag in range(n_agents):
            print('agent', ag)
            rand_par = 10 * np.random.rand(n_fit_par) - 5
            sim_par = model.simulate_agents(ag, rand_par)
            print('sim_par', sim_par)

            # Recover
            best_par = model.minimize_NLL(ag, n_fit_par, n_iter=n_iter)
            fit_par = trans.get_pars(agent_stuff, best_par)
            trans_par = trans.transform_pars(fit_par)
            print('trans_par', trans_par)
            NLL, BIC, AIC = model.calculate_fit(trans_par, ag, False)
            model.update_genrec_and_save(
                np.concatenate(([ag, learning_style, method, NLL, BIC, AIC], sim_par, trans_par)),
                agent_stuff['data_path'] + '/genrec.csv')

# Fit parameters to actual data
# agents = np.array([15, 16, 17, 18, 20, 22, 23, 24, 25, 31, 32, 33, 34, 35, 40, 42, 43, 44, 48, 49, 52, 53, 56, 60, 63, 65, 67])
#
# params0 = 0.5 * np.ones(len(agent_stuff['free_par']))
# NLL, BIC, AIC = model.calculate_fit(params0, agents[0], False)
# minimization = minimize(model.calculate_fit,
#                         params0, (agents[0], True),  # arguments to model.calculate_fit: id, only_NLL
#                         method='Nelder-Mead', options={'disp': True})
# fit_par = model.get_fit_par(minimization)
# NLL, BIC, AIC = model.calculate_fit(fit_par, agents[0], False)
# model.simulate_agents(fit_par)
