from main import *
import glob


# Set and check parameters
sets = {'run_on_cluster': False,
        'data_set': 'PS',  # 'PS' or 'Aliens'

	    #########################
	    ##### ADJUST ME!!! ######
        'fit_par_names': ['alpha', 'beta', 'epsilon'],
        'learning_style': 'simple_flat',
	    #########################
	    #########################

        'set_specific_parameters': False,
        'use_humans': True,
        'n_agents': 2}
check_user_settings(sets)

# Get data paths, plot paths, etc.
paths = get_paths(sets['use_humans'], sets['data_set'], sets['run_on_cluster'])
if sets['use_humans']:
    file_name_pattern = '*.csv'
else:
    file_name_pattern = '*' + sets['learning_style'] + '*.csv'
agent_ids = range(100, 102)

# Interactive game
# interactive_game(sets, paths['prob_switch_randomized_sequences'])

# # Simulate random agents based on the model specified above
# for agent_id in agent_ids:
#     simulate(sets, agent_id,
#              paths['agent_data_path'],
#              paths['prob_switch_randomized_sequences'])

# Fit data to files in the given directory (either human data or simulated agents)
for file_name in glob.glob(paths['agent_data_path'] + file_name_pattern):
    fit(sets, file_name,
        paths['fitted_data_path'],
        paths['heatmap_data_path'],
        paths['prob_switch_randomized_sequences'])

# Plot heatmaps to show how the fitting went
for agent_id in agent_ids:
    plot_heatmaps(sets, agent_id,
                  paths['heatmap_data_path'],
                  paths['heatmap_plot_path'])

# # Simulate data based on fitted parameters
# for file_name in glob.glob(paths['fitted_data_path'] + '*.csv'):
#     simulate_based_on_data(sets, file_name,
#                            paths['simulation_data_path'],
#                            paths['prob_switch_randomized_sequences'])
