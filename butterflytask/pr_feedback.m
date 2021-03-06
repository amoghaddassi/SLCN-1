function pr_feedback(trial, feedback_style)

global exp

%% Determine reward based on reward_sequence and reward_sequence_inc
trial_fly = exp.butterfly_sequence(trial);
if strcmp(feedback_style, 'deterministic')
    reward_if_correct = 1;
    reward_if_incorrect = 0;
else
    reward_if_correct = exp.reward_sequence(exp.n_correct(trial_fly), trial_fly);
    reward_if_incorrect = exp.reward_sequence_inc(exp.n_incorrect(trial_fly), trial_fly);
end

% When participant did not press any key, or pressed a wrong key
if isempty(exp.key) || ((exp.key(1) ~= exp.nkey.le) && (exp.key(1) ~= exp.nkey.ri))
    buffer = exp.buffer.incorrect;
% When participant will get a reward
elseif (exp.correct_response && reward_if_correct) || ...      % Correct butterfly picked; reward in 80% of trials, according to pre-randomized list
      (~exp.correct_response && reward_if_incorrect)       % Incorrect butterfly picked; reward in 20% of trials, according to pre-randomized list
    buffer = exp.buffer.correct;
    exp.earned_points = exp.earned_points + 1;
    exp.reward = 1;
% When participant will not get a reward
else
    buffer = exp.buffer.incorrect;
end

preparestring(strcat('Points: ', num2str(exp.earned_points)), buffer, exp.p.counter_x,300);
drawpict(buffer);
wait(exp.times.reward);
