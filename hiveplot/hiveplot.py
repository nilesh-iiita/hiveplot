import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from matplotlib.path import Path 


class HivePlot(object):
	"""
	The HivePlot class will take in the following and return
	a hive plot:
	- nodes: 	a dictionary of nodes, in which there are at most 3 keys
			 	in the dictionary, and the nodes are sorted in a
			 	pre-specified order. One common grouping is by a node 
			 	attribute and one possible ordering is by degree centrality.

	- edges: 	a list of (u,v,d) tuples (in NetworkX style), where u and v
			 	are the nodes to join, and d are the node attributes.

	The user will have to pre-sort and pre-group the nodes, and pre-map
	the edge color groupings. This code will determine the positioning
	and exact drawing of the edges.

	Hive plots are non-trivial to construct. These are the most important 
	features one has to consider:
	- 	Grouping of nodes: 
		- 	at most 3 groups.
	- 	Ordering of nodes: 
		- 	must have an ordinal or continuous node attribute
	- 	Cross-group edges:
		- 	Undirected is easier to draw than directed.
		- 	Directed is possible.
	- 	Within-group edges:
		- 	Requires the duplication of an axis.
	"""

	def __init__(self, nodes, edges, group_colormap, is_directed=False, scale=10):
		super(HivePlot, self).__init__()
		self.nodes = nodes #dictionary of {group:[ordered_nodes]}
		self.edges = edges #list of (u,v,d) tuples
		#simplified version of the edges:
		self.is_directed = is_directed #boolean of whether graph is supposed 
									   #to be directed or not
		self.fig = plt.figure(figsize=(8,8))
		self.ax = self.fig.add_subplot(111)
		self.scale = scale
		self.dot_radius = self.scale / float(4)
		self.internal_radius = scale ** 2
		self.group_colormap = group_colormap #dictionary of group:color
		self.draw()
		

	"""
	Steps in graph drawing:
	1. 	Determine the number of groups. This in turn determines the number of 
		axes to draw, and the major angle between the axes.
	
	2. 	For each group, determine whether there are edges between members of 
		the same group.
		a. 	If True:
			-	Duplicate the axis by shifting off by a minor angle.
			- 	Draw each axis line, with length proportional to number of 
				nodes in the group:
				-	One is at major angle + minor angle
				-	One is at major angle - minor angle
			-	Draw in the nodes.
		b. 	If False:
			- 	Draw the axis line at the major angle.
			-	Length of axis line is proportional to the number of nodes in 
				the group
			-	Draw in the nodes.

	3. 	Determine which node group is at the 0 radians position. The angles 
		that are calculated will have to be adjusted for whether it is at 2*pi 
		radians or at 0 radians, depending on the angle differences.
	
	4. 	For each edge, determine the radial position of the start node and end 
		node. Compute the middle angle and the mean radius of the start and 
		end nodes. 
	"""
	def simplified_edges(self):
		for u, v, d in self.edges:
			yield (u, v)

	def major_angle(self):
		"""
		Computes the major angle: 2pi radians / number of groups.
		"""
		num_groups = len(self.nodes.keys())
		return 2 * np.pi / num_groups
	
	def minor_angle(self):
		"""
		Computes the minor angle: 2pi radians / 3 * number of groups.
		"""
		num_groups = len(self.nodes.keys())

		return 2 * np.pi / (6 * num_groups)

	def plot_radius(self):
		"""
		Computes the plot radius: maximum of length of each list of nodes.
		"""
		plot_R = 0
		for group, nodelist in self.nodes.items():
			proposed_radius = len(nodelist) * self.scale
			if proposed_radius > plot_R:
				plot_R = proposed_radius
		return plot_R + self.internal_radius

	def axis_length(self, group):
		"""
		Computes the length of the axis for a given group.
		"""
		return len(self.nodes[group])

	def has_edge_within_group(self, group):
		assert group in self.nodes.keys(), "{0} not one of the group of nodes".format(group)
		nodelist = self.nodes[group]
		for n1, n2 in self.simplified_edges():
			if n1 in nodelist and n2 in nodelist:
				return True

	def plot_axis(self, rs, theta):
		xs, ys = get_cartesian(rs, theta)
		self.ax.plot(xs, ys, 'black')

	def plot_nodes(self, nodelist, theta, group):
		for i, node in enumerate(nodelist):
			r = self.internal_radius + i * self.scale
			x, y = get_cartesian(r, theta)
			circle = plt.Circle(xy=(x,y), radius=self.dot_radius, color=self.group_colormap[group])
			self.ax.add_patch(circle)

	def group_theta(self, group):
		"""
		Computes the theta along which a group's nodes are aligned.
		"""
		return self.nodes.keys().index(group) * self.major_angle()
		
	def add_axes_and_nodes(self):
		for i, (group, nodelist) in enumerate(self.nodes.items()):
			theta = self.group_theta(group)
			rs = np.arange(self.internal_radius, self.internal_radius + self.scale * len(nodelist))

			if self.has_edge_within_group(group):
					theta = theta - self.minor_angle()
					self.plot_axis(rs, theta)
					self.plot_nodes(nodelist, theta, group)

					theta = theta + 2 * self.minor_angle()
					self.plot_axis(rs, theta)
					self.plot_nodes(nodelist, theta, group)

			else:
				self.plot_axis(rs, theta)
				self.plot_nodes(nodelist, theta, group)


	def find_group_membership(self, node):
		"""
		Identifies the group for which a node belongs to.
		"""
		for group, nodelist in self.nodes.items():
			if node in nodelist:
				return group

	def get_idx(self, node):
		"""
		Finds the index of the node in the sorted list.
		"""
		group = self.find_group_membership(node)
		return self.nodes[group].index(node)

	def node_radius(self, node):
		"""
		Computes the radial position of the node.
		"""
		return self.get_idx(node) * self.scale + self.internal_radius

	def node_theta(self, node):
		"""
		Convenience function to find the node's theta angle.
		"""
		group = self.find_group_membership(node)
		return self.group_theta(group)

	def draw_edge(self, n1, n2, d):
		start_radius = self.node_radius(n1)
		start_theta = self.node_theta(n1)

		end_radius = self.node_radius(n2)
		end_theta = self.node_theta(n2)

		start_theta, end_theta = self.correct_angles(start_theta, end_theta)
		start_theta, end_theta = self.adjust_angles(n1, start_theta, n2, end_theta)


		middle1_radius = np.min([start_radius, end_radius])
		middle2_radius = np.max([start_radius, end_radius])

		if start_radius > end_radius:
			middle1_radius, middle2_radius = middle2_radius, middle1_radius

		middle1_theta = np.mean([start_theta, end_theta])
		middle2_theta = np.mean([start_theta, end_theta])

		startx, starty = get_cartesian(start_radius, start_theta)
		middle1x, middle1y = get_cartesian(middle1_radius, middle1_theta)
		middle2x, middle2y = get_cartesian(middle2_radius, middle2_theta)
		endx, endy = get_cartesian(end_radius, end_theta)

		verts = [(startx, starty), (middle1x, middle1y), (middle2x, middle2y), (endx, endy)]
		codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4]

		path = Path(verts, codes)
		patch = patches.PathPatch(path, lw=1, facecolor='none', alpha=0.3)
		self.ax.add_patch(patch)

	def add_edges(self):
		for u, v, d in self.edges:
			self.draw_edge(u, v, d)

 	def draw(self):
		self.ax.set_xlim(-self.plot_radius(), self.plot_radius())
		self.ax.set_ylim(-self.plot_radius(), self.plot_radius())

		self.add_axes_and_nodes()
		self.add_edges()

		self.ax.axis('off')

	def adjust_angles(self, start_node, start_angle, end_node, end_angle):
		"""
		This function adjusts the start and end angles to correct for 
		duplicated axes.
		"""
		start_group = self.find_group_membership(start_node)
		end_group = self.find_group_membership(end_node)

		start_group_idx = self.nodes.keys().index(start_group)
		end_group_idx = self.nodes.keys().index(end_group)

		if start_group_idx < end_group_idx:
			end_angle = end_angle - self.minor_angle()
			start_angle = start_angle + self.minor_angle()

		if end_group_idx < start_group_idx:
			start_angle = start_angle - self.minor_angle()
			end_angle = end_angle + self.minor_angle()

		if start_group_idx == 0 and end_group_idx == len(self.nodes.keys())-1:
			start_angle = start_angle - self.minor_angle() * 2
			end_angle = end_angle + self.minor_angle() * 2

		if start_group_idx == len(self.nodes.keys())-1 and end_group_idx == 0:
			start_angle = start_angle + self.minor_angle() * 2
			end_angle = end_angle - self.minor_angle() * 2


		return start_angle, end_angle
	def correct_angles(self, start_angle, end_angle):
		"""
		This function corrects for the following problems in the edges:
		"""
		# Edges going the wrong direction.
		if start_angle == 0 and (end_angle - start_angle > np.pi):
			start_angle = np.pi * 2
		if end_angle == 0 and (end_angle - start_angle < -np.pi):
			end_angle = np.pi * 2

		# Case when start_angle == end_angle:
		if start_angle == end_angle:
			start_angle = start_angle - self.minor_angle()
			end_angle = end_angle + self.minor_angle()
			

		return start_angle, end_angle


"""
Global helper functions go here
"""
def get_cartesian(r, theta):
	x = r*np.sin(theta)
	y = r*np.cos(theta)

	return x, y



	
