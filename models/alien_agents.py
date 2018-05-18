import numpy as np
import math


class Agent(object):
    def __init__(self, agent_stuff, all_params_lim, task_stuff=np.nan):

        # Get parameters
        self.n_actions = task_stuff['n_actions']
        self.n_TS = agent_stuff['n_TS']
        self.n_contexts = task_stuff['n_contexts']
        self.n_aliens = task_stuff['n_aliens']
        self.learning_style = agent_stuff['learning_style']
        self.select_deterministic = 'flat' in self.learning_style  # Hack to select the right TS each time for the flat agent
        self.mix_probs = agent_stuff['mix_probs']
        self.id = agent_stuff['id']
        [self.alpha, self.beta, self.epsilon, self.forget, self.suppress_prev_TS] = all_params_lim
        self.alpha_high = self.alpha  # TD
        self.beta_high = self.beta
        self.forget_high = self.forget
        self.phase = np.nan
        assert self.alpha > 0  # Make sure that alpha is a number and is > 0
        assert self.beta >= 1
        assert self.epsilon >= 0
        assert self.mix_probs in [True, False]
        assert self.learning_style in ['s-flat', 'flat', 'hierarchical']

        # Set up values at low (stimulus-action) level
        self.initial_q_low = 5. / 3.  # Average reward per alien during training / number of actions
        if 'flat' in self.learning_style:
            Q_low_dim = [self.n_contexts, self.n_aliens, self.n_actions]
        elif self.learning_style == 'hierarchical':
            Q_low_dim = [self.n_TS, self.n_aliens, self.n_actions]
        self.Q_low = self.initial_q_low * np.ones(Q_low_dim) +\
            np.random.normal(0, self.initial_q_low / 100, Q_low_dim)  # jitter avoids identical values

        # Set up values at high (context-TS) level
        if self.learning_style == 's-flat':
            self.Q_high = np.zeros([self.n_contexts, self.n_TS])
            self.Q_high[:, 0] = 1  # First col == 1 => Every context uses the same 1 TS
        elif self.learning_style == 'flat':
            self.Q_high = np.eye(self.n_contexts)  # np.eye => agent always selects appropriate TS
        elif self.learning_style == 'hierarchical':
            self.initial_q_high = self.initial_q_low
            self.Q_high = np.nan

        # Initialize action probs, current TS and action, LL
        self.p_TS = np.ones(self.n_TS) / self.n_TS  # P(TS|context)
        self.p_actions = np.ones(self.n_actions) / self.n_actions  # P(action|TS)
        self.Q_actions = np.nan
        self.RPEs_low = np.nan
        self.RPEs_high = np.nan
        self.TS = np.nan
        self.prev_action = []
        self.context = 99
        self.LL = 0
        self.seen_contexts = []

        # Stuff for competition phase
        self.p_stimuli = np.nan
        self.Q_stimuli = np.nan

    def select_action(self, stimulus):
        if self.context != stimulus[0]:  # detect context switch
            self.handle_context_switches(stimulus[0])
        self.p_TS = self.get_p_from_Q(Q=self.Q_high[stimulus[0], :], beta=self.beta_high, epsilon=0, select_deterministic=self.select_deterministic)
        self.TS = np.random.choice(len(self.p_TS), p=self.p_TS)
        if self.mix_probs:
            self.Q_actions = np.dot(self.p_TS, self.Q_low[:, stimulus[1], :])  # Weighted average for Q_low of all TS
        else:
            self.Q_actions = self.Q_low[self.TS, stimulus[1], :]  # Q_low of the highest-valued TS
        self.p_actions = self.get_p_from_Q(Q=self.Q_actions, beta=self.beta, epsilon=self.epsilon)
        self.prev_action = np.random.choice(range(self.n_actions), p=self.p_actions)
        self.forget_Qs()
        return self.prev_action

    def handle_context_switches(self, context):
        if context not in self.seen_contexts:  # if a completely new context is encountered
            jitter = np.random.normal(0, self.initial_q_high / 100, [self.n_contexts, 1])
            new_TS = self.initial_q_high * np.ones([self.n_contexts, 1]) + jitter  # create new TS
            if not self.seen_contexts:  # if this is the first context ever encountered (very first trial)
                self.Q_high = new_TS
            else:
                self.Q_high = np.append(self.Q_high, new_TS, axis=1)  # add column with new TS
            # print('Initial TS values for context {0}: {1}'.format(context, np.round(new_TS, 3)))
            self.seen_contexts.append(context)
        self.Q_high[context, np.argmax(self.p_TS)] *= (1 - self.suppress_prev_TS)  # suppress previous TS
        self.context = context

    def learn(self, stimulus, action, reward):
        self.update_Qs(stimulus, action, reward)
        self.update_LL(action)

    def get_p_from_Q(self, Q, beta, epsilon, select_deterministic=False):
        if select_deterministic:
            assert(np.sum(Q == 1) == 1)  # Verify that exactly 1 Q-value == 1 (Q_high for the flat agent)
            p_actions = np.array(Q == 1, dtype=int)  # select the one TS that has a value of 1 (all others are 0)
        else:
            # Softmax
            p_actions = np.empty(len(Q))
            for i in range(len(Q)):
                denominator = 1. + sum([np.exp(beta * (Q[j] - Q[i])) for j in range(len(Q)) if j != i])
                p_actions[i] = 1. / denominator
            # Add epsilon noise
            p_actions = epsilon / len(p_actions) + (1 - epsilon) * p_actions
        assert np.round(sum(p_actions), 3) == 1
        return p_actions

    def update_Qs(self, stimulus, action, reward):
        # Calculate prediction errors
        self.RPEs_high = reward - self.Q_high[stimulus[0], :]  # Q_high for all TSs, given context
        self.RPEs_low = reward - self.Q_low[:, stimulus[1], action]  # Q_low for all TSs, given alien & action
        if self.mix_probs:
            self.Q_low[:, stimulus[1], action] += self.alpha * self.p_TS * self.RPEs_low  # flat agent: p_TS has just one 1
            if self.learning_style == 'hierarchical':
                self.Q_high[stimulus[0], :] += self.alpha_high * self.p_TS * self.RPEs_high
        else:
            self.Q_low[self.TS, stimulus[1], action] += self.alpha * self.RPEs_low[self.TS]
            if self.learning_style == 'hierarchical':
                self.Q_high[stimulus[0], self.TS] += self.alpha_high * self.RPEs_high[self.TS]

    def forget_Qs(self):
        self.Q_low -= self.forget * (self.Q_low - 1)  # decays toward 1 (average of incorrect responses)
        if self.learning_style == 'hierarchical':
            self.Q_high -= self.forget_high * (self.Q_high - 1)  # decays toward 1 (average of incorrect responses)

    def update_LL(self, action):
        self.LL += np.log(self.p_actions[action])
        # assert action == self.prev_action  # obviously fails when called in calculate_NLL

    def competition_selection(self, stimuli, phase):
        self.Q_stimuli = [self.get_Q_for_stimulus(stimulus, phase) for stimulus in stimuli]
        self.p_stimuli = self.get_p_from_Q(self.Q_stimuli, self.beta, self.epsilon)
        selected_index = np.random.choice(range(len(stimuli)), p=self.p_stimuli)
        return stimuli[selected_index]

    def marginalize(self, Q, beta):
        # Calculates the weighted average of the entries in Q: \sum_{a_i} p(a_i) * Q(a_i)
        p = self.get_p_from_Q(Q, beta, self.epsilon)
        return np.dot(p, Q)

    def get_p_TSi(self):
        # \pi(TS_i) = \sum_{c_j} \pi(TS_i|c_j) p(c_j)
        p_TSi_given_cj = [self.get_p_from_Q(self.Q_high[c, :], self.beta_high, self.epsilon) for c in range(self.n_contexts)]
        return np.mean(p_TSi_given_cj, axis=0)

    def get_Q_for_stimulus(self, stimulus, phase):
        if phase == 'contexts':
            # Calculate "stimulus values": Q(c) = \sum_{TS_i} \pi(TS_i|c) Q(TS_i|c)
            Q_TSi_given_c = self.Q_high[stimulus, :]
            return self.marginalize(Q_TSi_given_c, self.beta_high)

        elif phase == 'context-aliens':
            # Also "stimulus values"
            context = stimulus[0]
            alien = stimulus[1]

            # Q(s|TS) = \sum_{a_i} \pi(a_i|s,TS) Q(a_i|s,TS)
            Q_ai_given_s_TSi = self.Q_low[:, alien, :]
            Q_s_given_TSi = [self.marginalize(Q_ai_given_s_TSi[TSi, :], self.beta) for TSi in range(self.n_TS)]

            # \pi(TS_i|c) = softmax(Q(TS_i|c))
            Q_TSi_given_c = self.Q_high[context, :]
            p_TSi_given_c = self.get_p_from_Q(Q_TSi_given_c, self.beta_high, self.epsilon)

            # Q(s,c) = \sum_{TS_i} \pi(TS_i|c) Q(s|TS_i)
            return np.dot(Q_s_given_TSi, p_TSi_given_c)

        elif phase == 'items':
            item = stimulus

            # Q(a|TS) = \sum_{s_i} \pi(a|s_i,TS) Q(a|s_i,TS)
            Q_a_given_s_TS = self.Q_low[:, :, item]
            Q_a_given_TS = [self.marginalize(Q_a_given_s_TS[TSi, :], self.beta) for TSi in range(self.n_TS)]

            # Q(a) = \sum_{TS_i} Q(a|TS_i) \pi(TS_i)
            p_TSi = self.get_p_TSi()
            return np.dot(Q_a_given_TS, p_TSi)

        elif phase == 'aliens':
            alien = stimulus

            # Q(s|TS) = \sum_{a_i} \pi(a_i|s,TS) Q(a_i|s,TS)
            Q_a_given_s_TS = self.Q_low[:, alien, :]
            Q_s_given_TS = [self.marginalize(Q_a_given_s_TS[TSi, :], beta=self.beta) for TSi in range(self.n_TS)]

            # Q(s) = \sum_{TS_i} Q(s|TS_i) \pi(TS_i)
            p_TSi = self.get_p_TSi()
            return np.dot(Q_s_given_TS, p_TSi)
