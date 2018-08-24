raw_dirs = []
raw_dirs.append('../eye_tracker/eye_tracking-selected/suffrage_a/')
raw_dirs.append('../eye_tracker/eye_tracking-selected/suffrage_b/')
data_dir = '../pipeline-data/'
# highlight colors
highlight_colors = {'dark blue':(71,148,241), 'yellow':(253, 250, 193), 'light blue':(213, 242, 254), 'white':(245, 245, 245), 'black':(90,90,90)}
highlight_color_pairs = {
	'dark blue': (highlight_colors['white'], highlight_colors['dark blue']),
	'light blue':(highlight_colors['light blue'], highlight_colors['black']),
	'yellow':(highlight_colors['yellow'], highlight_colors['black']),
	'white':(highlight_colors['white'], highlight_colors['black'])
}