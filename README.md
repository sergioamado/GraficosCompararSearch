# GraficosCompararSearch
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Search for AIMA 4th edition\n",
    "\n",
    "Implementation of search algorithms and search problems for AIMA.\n",
    "\n",
    "# Problems and Nodes\n",
    "\n",
    "We start by defining the abstract class for a `Problem`; specific problem domains will subclass this. To make it easier for algorithms that use a heuristic evaluation function, `Problem` has a default `h` function (uniformly zero), and subclasses can define their own default `h` function.\n",
    "\n",
    "We also define a `Node` in a search tree, and some functions on nodes: `expand` to generate successors; `path_actions` and `path_states`  to recover aspects of the path from the node.  "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 93,
   "metadata": {},
   "outputs": [],
   "source": [
    "%matplotlib inline\n",
    "import matplotlib.pyplot as plt\n",
    "import random\n",
    "import heapq\n",
    "import math\n",
    "import sys\n",
    "from collections import defaultdict, deque, Counter\n",
    "from itertools import combinations\n",
    "\n",
    "\n",
    "class Problem(object):\n",
    "    \"\"\"The abstract class for a formal problem. A new domain subclasses this,\n",
    "    overriding `actions` and `results`, and perhaps other methods.\n",
    "    The default heuristic is 0 and the default action cost is 1 for all states.\n",
    "    When yiou create an instance of a subclass, specify `initial`, and `goal` states \n",
    "    (or give an `is_goal` method) and perhaps other keyword args for the subclass.\"\"\"\n",
    "\n",
    "    def __init__(self, initial=None, goal=None, **kwds): \n",
    "        self.__dict__.update(initial=initial, goal=goal, **kwds) \n",
    "        \n",
    "    def actions(self, state):        raise NotImplementedError\n",
    "    def result(self, state, action): raise NotImplementedError\n",
    "    def is_goal(self, state):        return state == self.goal\n",
    "    def action_cost(self, s, a, s1): return 1\n",
    "    def h(self, node):               return 0\n",
    "    \n",
    "    def __str__(self):\n",
    "        return '{}({!r}, {!r})'.format(\n",
    "            type(self).__name__, self.initial, self.goal)\n",
    "    \n",
    "\n",
    "class Node:\n",
    "    \"A Node in a search tree.\"\n",
    "    def __init__(self, state, parent=None, action=None, path_cost=0):\n",
    "        self.__dict__.update(state=state, parent=parent, action=action, path_cost=path_cost)\n",
    "\n",
    "    def __repr__(self): return '<{}>'.format(self.state)\n",
    "    def __len__(self): return 0 if self.parent is None else (1 + len(self.parent))\n",
    "    def __lt__(self, other): return self.path_cost < other.path_cost\n",
    "    \n",
    "    \n",
    "failure = Node('failure', path_cost=math.inf) # Indicates an algorithm couldn't find a solution.\n",
    "cutoff  = Node('cutoff',  path_cost=math.inf) # Indicates iterative deepening search was cut off.\n",
    "    \n",
    "    \n",
    "def expand(problem, node):\n",
    "    \"Expand a node, generating the children nodes.\"\n",
    "    s = node.state\n",
    "    for action in problem.actions(s):\n",
    "        s1 = problem.result(s, action)\n",
    "        cost = node.path_cost + problem.action_cost(s, action, s1)\n",
    "        yield Node(s1, node, action, cost)\n",
    "        \n",
    "\n",
    "def path_actions(node):\n",
    "    \"The sequence of actions to get to this node.\"\n",
    "    if node.parent is None:\n",
    "        return []  \n",
    "    return path_actions(node.parent) + [node.action]\n",
    "\n",
    "\n",
    "def path_states(node):\n",
    "    \"The sequence of states to get to this node.\"\n",
    "    if node in (cutoff, failure, None): \n",
    "        return []\n",
    "    return path_states(node.parent) + [node.state]"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Queues\n",
    "\n",
    "First-in-first-out and Last-in-first-out queues, and a `PriorityQueue`, which allows you to keep a collection of items, and continually remove from it the item with minimum `f(item)` score."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 2,
   "metadata": {},
   "outputs": [],
   "source": [
    "FIFOQueue = deque\n",
    "\n",
    "LIFOQueue = list\n",
    "\n",
    "class PriorityQueue:\n",
    "    \"\"\"A queue in which the item with minimum f(item) is always popped first.\"\"\"\n",
    "\n",
    "    def __init__(self, items=(), key=lambda x: x): \n",
    "        self.key = key\n",
    "        self.items = [] # a heap of (score, item) pairs\n",
    "        for item in items:\n",
    "            self.add(item)\n",
    "         \n",
    "    def add(self, item):\n",
    "        \"\"\"Add item to the queuez.\"\"\"\n",
    "        pair = (self.key(item), item)\n",
    "        heapq.heappush(self.items, pair)\n",
    "\n",
    "    def pop(self):\n",
    "        \"\"\"Pop and return the item with min f(item) value.\"\"\"\n",
    "        return heapq.heappop(self.items)[1]\n",
    "    \n",
    "    def top(self): return self.items[0][1]\n",
    "\n",
    "    def __len__(self): return len(self.items)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Search Algorithms: Best-First\n",
    "\n",
    "Best-first search with various *f(n)* functions gives us different search algorithms. Note that A\\*, weighted A\\* and greedy search can be given a heuristic function, `h`, but if `h` is not supplied they use the problem's default `h` function (if the problem does not define one, it is taken as *h(n)* = 0)."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 356,
   "metadata": {},
   "outputs": [],
   "source": [
    "def best_first_search(problem, f):\n",
    "    \"Search nodes with minimum f(node) value first.\"\n",
    "    node = Node(problem.initial)\n",
    "    frontier = PriorityQueue([node], key=f)\n",
    "    reached = {problem.initial: node}\n",
    "    while frontier:\n",
    "        node = frontier.pop()\n",
    "        if problem.is_goal(node.state):\n",
    "            return node\n",
    "        for child in expand(problem, node):\n",
    "            s = child.state\n",
    "            if s not in reached or child.path_cost < reached[s].path_cost:\n",
    "                reached[s] = child\n",
    "                frontier.add(child)\n",
    "    return failure\n",
    "\n",
    "\n",
    "def best_first_tree_search(problem, f):\n",
    "    \"A version of best_first_search without the `reached` table.\"\n",
    "    frontier = PriorityQueue([Node(problem.initial)], key=f)\n",
    "    while frontier:\n",
    "        node = frontier.pop()\n",
    "        if problem.is_goal(node.state):\n",
    "            return node\n",
    "        for child in expand(problem, node):\n",
    "            if not is_cycle(child):\n",
    "                frontier.add(child)\n",
    "    return failure\n",
    "\n",
    "\n",
    "def g(n): return n.path_cost\n",
    "\n",
    "\n",
    "def astar_search(problem, h=None):\n",
    "    \"\"\"Search nodes with minimum f(n) = g(n) + h(n).\"\"\"\n",
    "    h = h or problem.h\n",
    "    return best_first_search(problem, f=lambda n: g(n) + h(n))\n",
    "\n",
    "\n",
    "def astar_tree_search(problem, h=None):\n",
    "    \"\"\"Search nodes with minimum f(n) = g(n) + h(n), with no `reached` table.\"\"\"\n",
    "    h = h or problem.h\n",
    "    return best_first_tree_search(problem, f=lambda n: g(n) + h(n))\n",
    "\n",
    "\n",
    "def weighted_astar_search(problem, h=None, weight=1.4):\n",
    "    \"\"\"Search nodes with minimum f(n) = g(n) + weight * h(n).\"\"\"\n",
    "    h = h or problem.h\n",
    "    return best_first_search(problem, f=lambda n: g(n) + weight * h(n))\n",
    "\n",
    "        \n",
    "def greedy_bfs(problem, h=None):\n",
    "    \"\"\"Search nodes with minimum h(n).\"\"\"\n",
    "    h = h or problem.h\n",
    "    return best_first_search(problem, f=h)\n",
    "\n",
    "\n",
    "def uniform_cost_search(problem):\n",
    "    \"Search nodes with minimum path cost first.\"\n",
    "    return best_first_search(problem, f=g)\n",
    "\n",
    "\n",
    "def breadth_first_bfs(problem):\n",
    "    \"Search shallowest nodes in the search tree first; using best-first.\"\n",
    "    return best_first_search(problem, f=len)\n",
    "\n",
    "\n",
    "def depth_first_bfs(problem):\n",
    "    \"Search deepest nodes in the search tree first; using best-first.\"\n",
    "    return best_first_search(problem, f=lambda n: -len(n))\n",
    "\n",
    "\n",
    "def is_cycle(node, k=30):\n",
    "    \"Does this node form a cycle of length k or less?\"\n",
    "    def find_cycle(ancestor, k):\n",
    "        return (ancestor is not None and k > 0 and\n",
    "                (ancestor.state == node.state or find_cycle(ancestor.parent, k - 1)))\n",
    "    return find_cycle(node.parent, k)\n",
    "\n"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Other Search Algorithms\n",
    "\n",
    "Here are the other search algorithms:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 234,
   "metadata": {},
   "outputs": [],
   "source": [
    "def breadth_first_search(problem):\n",
    "    \"Search shallowest nodes in the search tree first.\"\n",
    "    node = Node(problem.initial)\n",
    "    if problem.is_goal(problem.initial):\n",
    "        return node\n",
    "    frontier = FIFOQueue([node])\n",
    "    reached = {problem.initial}\n",
    "    while frontier:\n",
    "        node = frontier.pop()\n",
    "        for child in expand(problem, node):\n",
    "            s = child.state\n",
    "            if problem.is_goal(s):\n",
    "                return child\n",
    "            if s not in reached:\n",
    "                reached.add(s)\n",
    "                frontier.appendleft(child)\n",
    "    return failure\n",
    "\n",
    "\n",
    "def iterative_deepening_search(problem):\n",
    "    \"Do depth-limited search with increasing depth limits.\"\n",
    "    for limit in range(1, sys.maxsize):\n",
    "        result = depth_limited_search(problem, limit)\n",
    "        if result != cutoff:\n",
    "            return result\n",
    "        \n",
    "        \n",
    "def depth_limited_search(problem, limit=10):\n",
    "    \"Search deepest nodes in the search tree first.\"\n",
    "    frontier = LIFOQueue([Node(problem.initial)])\n",
    "    result = failure\n",
    "    while frontier:\n",
    "        node = frontier.pop()\n",
    "        if problem.is_goal(node.state):\n",
    "            return node\n",
    "        elif len(node) >= limit:\n",
    "            result = cutoff\n",
    "        elif not is_cycle(node):\n",
    "            for child in expand(problem, node):\n",
    "                frontier.append(child)\n",
    "    return result\n",
    "\n",
    "\n",
    "def depth_first_recursive_search(problem, node=None):\n",
    "    if node is None: \n",
    "        node = Node(problem.initial)\n",
    "    if problem.is_goal(node.state):\n",
    "        return node\n",
    "    elif is_cycle(node):\n",
    "        return failure\n",
    "    else:\n",
    "        for child in expand(problem, node):\n",
    "            result = depth_first_recursive_search(problem, child)\n",
    "            if result:\n",
    "                return result\n",
    "        return failure"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 236,
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "['N', 'I', 'V', 'U', 'B', 'F', 'S', 'O', 'Z', 'A', 'T', 'L']"
      ]
     },
     "execution_count": 236,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "path_states(depth_first_recursive_search(r2))"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Bidirectional Best-First Search"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 412,
   "metadata": {},
   "outputs": [],
   "source": [
    "def bidirectional_best_first_search(problem_f, f_f, problem_b, f_b, terminated):\n",
    "    node_f = Node(problem_f.initial)\n",
    "    node_b = Node(problem_f.goal)\n",
    "    frontier_f, reached_f = PriorityQueue([node_f], key=f_f), {node_f.state: node_f}\n",
    "    frontier_b, reached_b = PriorityQueue([node_b], key=f_b), {node_b.state: node_b}\n",
    "    solution = failure\n",
    "    while frontier_f and frontier_b and not terminated(solution, frontier_f, frontier_b):\n",
    "        def S1(node, f):\n",
    "            return str(int(f(node))) + ' ' + str(path_states(node))\n",
    "        print('Bi:', S1(frontier_f.top(), f_f), S1(frontier_b.top(), f_b))\n",
    "        if f_f(frontier_f.top()) < f_b(frontier_b.top()):\n",
    "            solution = proceed('f', problem_f, frontier_f, reached_f, reached_b, solution)\n",
    "        else:\n",
    "            solution = proceed('b', problem_b, frontier_b, reached_b, reached_f, solution)\n",
    "    return solution\n",
    "\n",
    "def inverse_problem(problem):\n",
    "    if isinstance(problem, CountCalls):\n",
    "        return CountCalls(inverse_problem(problem._object))\n",
    "    else:\n",
    "        inv = copy.copy(problem)\n",
    "        inv.initial, inv.goal = inv.goal, inv.initial\n",
    "        return inv"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 413,
   "metadata": {},
   "outputs": [],
   "source": [
    "def bidirectional_uniform_cost_search(problem_f):\n",
    "    def terminated(solution, frontier_f, frontier_b):\n",
    "        n_f, n_b = frontier_f.top(), frontier_b.top()\n",
    "        return g(n_f) + g(n_b) > g(solution)\n",
    "    return bidirectional_best_first_search(problem_f, g, inverse_problem(problem_f), g, terminated)\n",
    "\n",
    "def bidirectional_astar_search(problem_f):\n",
    "    def terminated(solution, frontier_f, frontier_b):\n",
    "        nf, nb = frontier_f.top(), frontier_b.top()\n",
    "        return g(nf) + g(nb) > g(solution)\n",
    "    problem_f = inverse_problem(problem_f)\n",
    "    return bidirectional_best_first_search(problem_f, lambda n: g(n) + problem_f.h(n),\n",
    "                                           problem_b, lambda n: g(n) + problem_b.h(n), \n",
    "                                           terminated)\n",
    "   \n",
    "\n",
    "def proceed(direction, problem, frontier, reached, reached2, solution):\n",
    "    node = frontier.pop()\n",
    "    for child in expand(problem, node):\n",
    "        s = child.state\n",
    "        print('proceed', direction, S(child))\n",
    "        if s not in reached or child.path_cost < reached[s].path_cost:\n",
    "            frontier.add(child)\n",
    "            reached[s] = child\n",
    "            if s in reached2: # Frontiers collide; solution found\n",
    "                solution2 = (join_nodes(child, reached2[s]) if direction == 'f' else\n",
    "                             join_nodes(reached2[s], child))\n",
    "                #print('solution', path_states(solution2), solution2.path_cost, \n",
    "                # path_states(child), path_states(reached2[s]))\n",
    "                if solution2.path_cost < solution.path_cost:\n",
    "                    solution = solution2\n",
    "    return solution\n",
    "\n",
    "S = path_states\n",
    "\n",
    "#A-S-R + B-P-R => A-S-R-P + B-P\n",
    "def join_nodes(nf, nb):\n",
    "    \"\"\"Join the reverse of the backward node nb to the forward node nf.\"\"\"\n",
    "    #print('join', S(nf), S(nb))\n",
    "    join = nf\n",
    "    while nb.parent is not None:\n",
    "        cost = join.path_cost + nb.path_cost - nb.parent.path_cost\n",
    "        join = Node(nb.parent.state, join, nb.action, cost)\n",
    "        nb = nb.parent\n",
    "        #print('  now join', S(join), 'with nb', S(nb), 'parent', S(nb.parent))\n",
    "    return join\n",
    "    \n",
    "   "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "#A , B = uniform_cost_search(r1), uniform_cost_search(r2)\n",
    "#path_states(A), path_states(B)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "#path_states(append_nodes(A, B))"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# TODO: RBFS"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Problem Domains\n",
    "\n",
    "Now we turn our attention to defining some problem domains as subclasses of `Problem`."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Route Finding Problems\n",
    "\n",
    "![](romania.png)\n",
    "\n",
    "In a `RouteProblem`, the states are names of \"cities\" (or other locations), like `'A'` for Arad. The actions are also city names; `'Z'` is the action to move to city `'Z'`. The layout of cities is given by a separate data structure, a `Map`, which is a graph where there are vertexes (cities), links between vertexes, distances (costs) of those links (if not specified, the default is 1 for every link), and optionally the 2D (x, y) location of each city can be specified. A `RouteProblem` takes this `Map` as input and allows actions to move between linked cities. The default heuristic is straight-line distance to the goal, or is uniformly zero if locations were not given."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 398,
   "metadata": {},
   "outputs": [],
   "source": [
    "class RouteProblem(Problem):\n",
    "    \"\"\"A problem to find a route between locations on a `Map`.\n",
    "    Create a problem with RouteProblem(start, goal, map=Map(...)}).\n",
    "    States are the vertexes in the Map graph; actions are destination states.\"\"\"\n",
    "    \n",
    "    def actions(self, state): \n",
    "        \"\"\"The places neighboring `state`.\"\"\"\n",
    "        return self.map.neighbors[state]\n",
    "    \n",
    "    def result(self, state, action):\n",
    "        \"\"\"Go to the `action` place, if the map says that is possible.\"\"\"\n",
    "        return action if action in self.map.neighbors[state] else state\n",
    "    \n",
    "    def action_cost(self, s, action, s1):\n",
    "        \"\"\"The distance (cost) to go from s to s1.\"\"\"\n",
    "        return self.map.distances[s, s1]\n",
    "    \n",
    "    def h(self, node):\n",
    "        \"Straight-line distance between state and the goal.\"\n",
    "        locs = self.map.locations\n",
    "        return straight_line_distance(locs[node.state], locs[self.goal])\n",
    "    \n",
    "    \n",
    "def straight_line_distance(A, B):\n",
    "    \"Straight-line distance between two points.\"\n",
    "    return sum(abs(a - b)**2 for (a, b) in zip(A, B)) ** 0.5"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 16,
   "metadata": {},
   "outputs": [],
   "source": [
    "class Map:\n",
    "    \"\"\"A map of places in a 2D world: a graph with vertexes and links between them. \n",
    "    In `Map(links, locations)`, `links` can be either [(v1, v2)...] pairs, \n",
    "    or a {(v1, v2): distance...} dict. Optional `locations` can be {v1: (x, y)} \n",
    "    If `directed=False` then for every (v1, v2) link, we add a (v2, v1) link.\"\"\"\n",
    "\n",
    "    def __init__(self, links, locations=None, directed=False):\n",
    "        if not hasattr(links, 'items'): # Distances are 1 by default\n",
    "            links = {link: 1 for link in links}\n",
    "        if not directed:\n",
    "            for (v1, v2) in list(links):\n",
    "                links[v2, v1] = links[v1, v2]\n",
    "        self.distances = links\n",
    "        self.neighbors = multimap(links)\n",
    "        self.locations = locations or defaultdict(lambda: (0, 0))\n",
    "\n",
    "        \n",
    "def multimap(pairs) -> dict:\n",
    "    \"Given (key, val) pairs, make a dict of {key: [val,...]}.\"\n",
    "    result = defaultdict(list)\n",
    "    for key, val in pairs:\n",
    "        result[key].append(val)\n",
    "    return result"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 400,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Some specific RouteProblems\n",
    "\n",
    "romania = Map(\n",
    "    {('O', 'Z'):  71, ('O', 'S'): 151, ('A', 'Z'): 75, ('A', 'S'): 140, ('A', 'T'): 118, \n",
    "     ('L', 'T'): 111, ('L', 'M'):  70, ('D', 'M'): 75, ('C', 'D'): 120, ('C', 'R'): 146, \n",
    "     ('C', 'P'): 138, ('R', 'S'):  80, ('F', 'S'): 99, ('B', 'F'): 211, ('B', 'P'): 101, \n",
    "     ('B', 'G'):  90, ('B', 'U'):  85, ('H', 'U'): 98, ('E', 'H'):  86, ('U', 'V'): 142, \n",
    "     ('I', 'V'):  92, ('I', 'N'):  87, ('P', 'R'): 97},\n",
    "    {'A': ( 76, 497), 'B': (400, 327), 'C': (246, 285), 'D': (160, 296), 'E': (558, 294), \n",
    "     'F': (285, 460), 'G': (368, 257), 'H': (548, 355), 'I': (488, 535), 'L': (162, 379),\n",
    "     'M': (160, 343), 'N': (407, 561), 'O': (117, 580), 'P': (311, 372), 'R': (227, 412),\n",
    "     'S': (187, 463), 'T': ( 83, 414), 'U': (471, 363), 'V': (535, 473), 'Z': (92, 539)})\n",
    "\n",
    "\n",
    "r0 = RouteProblem('A', 'A', map=romania)\n",
    "r1 = RouteProblem('A', 'B', map=romania)\n",
    "r2 = RouteProblem('N', 'L', map=romania)\n",
    "r3 = RouteProblem('E', 'T', map=romania)\n",
    "r4 = RouteProblem('O', 'M', map=romania)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 232,
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "['A', 'S', 'R', 'P', 'B']"
      ]
     },
     "execution_count": 232,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "path_states(uniform_cost_search(r1)) # Lowest-cost path from Arab to Bucharest"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 233,
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "['A', 'S', 'F', 'B']"
      ]
     },
     "execution_count": 233,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "path_states(breadth_first_search(r1)) # Breadth-first: fewer steps, higher path cost"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Grid Problems\n",
    "\n",
    "A `GridProblem` involves navigating on a 2D grid, with some cells being impassible obstacles. By default you can move to any of the eight neighboring cells that are not obstacles (but in a problem instance you can supply a `directions=` keyword to change that). Again, the default heuristic is straight-line distance to the goal. States are `(x, y)` cell locations, such as `(4, 2)`, and actions are `(dx, dy)` cell movements, such as `(0, -1)`, which means leave the `x` coordinate alone, and decrement the `y` coordinate by 1."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 20,
   "metadata": {},
   "outputs": [],
   "source": [
    "class GridProblem(Problem):\n",
    "    \"\"\"Finding a path on a 2D grid with obstacles. Obstacles are (x, y) cells.\"\"\"\n",
    "\n",
    "    def __init__(self, initial=(15, 30), goal=(130, 30), obstacles=(), **kwds):\n",
    "        Problem.__init__(self, initial=initial, goal=goal, \n",
    "                         obstacles=set(obstacles) - {initial, goal}, **kwds)\n",
    "\n",
    "    directions = [(-1, -1), (0, -1), (1, -1),\n",
    "                  (-1, 0),           (1,  0),\n",
    "                  (-1, +1), (0, +1), (1, +1)]\n",
    "    \n",
    "    def action_cost(self, s, action, s1): return straight_line_distance(s, s1)\n",
    "    \n",
    "    def h(self, node): return straight_line_distance(node.state, self.goal)\n",
    "                  \n",
    "    def result(self, state, action): \n",
    "        \"Both states and actions are represented by (x, y) pairs.\"\n",
    "        return action if action not in self.obstacles else state\n",
    "    \n",
    "    def actions(self, state):\n",
    "        \"\"\"You can move one cell in any of `directions` to a non-obstacle cell.\"\"\"\n",
    "        x, y = state\n",
    "        return {(x + dx, y + dy) for (dx, dy) in self.directions} - self.obstacles\n",
    "    \n",
    "class ErraticVacuum(Problem):\n",
    "    def actions(self, state): \n",
    "        return ['suck', 'forward', 'backward']\n",
    "    \n",
    "    def results(self, state, action): return self.table[action][state]\n",
    "    \n",
    "    table = dict(suck=    {1:{5,7}, 2:{4,8}, 3:{7}, 4:{2,4}, 5:{1,5}, 6:{8}, 7:{3,7}, 8:{6,8}},\n",
    "                 forward= {1:{2}, 2:{2}, 3:{4}, 4:{4}, 5:{6}, 6:{6}, 7:{8}, 8:{8}},\n",
    "                 backward={1:{1}, 2:{1}, 3:{3}, 4:{3}, 5:{5}, 6:{5}, 7:{7}, 8:{7}})"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 21,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Some grid routing problems\n",
    "\n",
    "# The following can be used to create obstacles:\n",
    "    \n",
    "def random_lines(X=range(15, 130), Y=range(60), N=150, lengths=range(6, 12)):\n",
    "    \"\"\"The set of cells in N random lines of the given lengths.\"\"\"\n",
    "    result = set()\n",
    "    for _ in range(N):\n",
    "        x, y = random.choice(X), random.choice(Y)\n",
    "        dx, dy = random.choice(((0, 1), (1, 0)))\n",
    "        result |= line(x, y, dx, dy, random.choice(lengths))\n",
    "    return result\n",
    "\n",
    "def line(x, y, dx, dy, length):\n",
    "    \"\"\"A line of `length` cells starting at (x, y) and going in (dx, dy) direction.\"\"\"\n",
    "    return {(x + i * dx, y + i * dy) for i in range(length)}\n",
    "\n",
    "random.seed(42) # To make this reproducible\n",
    "\n",
    "frame = line(-10, 20, 0, 1, 20) | line(150, 20, 0, 1, 20)\n",
    "cup = line(102, 44, -1, 0, 15) | line(102, 20, -1, 0, 20) | line(102, 44, 0, -1, 24)\n",
    "\n",
    "d1 = GridProblem(obstacles=random_lines(N=100) | frame)\n",
    "d2 = GridProblem(obstacles=random_lines(N=150) | frame)\n",
    "d3 = GridProblem(obstacles=random_lines(N=200) | frame)\n",
    "d4 = GridProblem(obstacles=random_lines(N=250) | frame)\n",
    "d5 = GridProblem(obstacles=random_lines(N=300) | frame)\n",
    "d6 = GridProblem(obstacles=cup | frame)\n",
    "d7 = GridProblem(obstacles=cup | frame | line(50, 35, 0, -1, 10) | line(60, 37, 0, -1, 17) | line(70, 31, 0, -1, 19))"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 8 Puzzle Problems\n",
    "\n",
    "![](https://ece.uwaterloo.ca/~dwharder/aads/Algorithms/N_puzzles/images/puz3.png)\n",
    "\n",
    "A sliding tile puzzle where you can swap the blank with an adjacent piece, trying to reach a goal configuration. The cells are numbered 0 to 8, starting at the top left and going row by row left to right. The pieces are numebred 1 to 8, with 0 representing the blank. An action is the cell index number that is to be swapped with the blank (*not* the actual number to be swapped but the index into the state). So the diagram above left is the state `(5, 2, 7, 8, 4, 0, 1, 3, 6)`, and the action is `8`, because the cell number 8 (the 9th or last cell, the `6` in the bottom right) is swapped with the blank.\n",
    "\n",
    "There are two disjoint sets of states that cannot be reached from each other. One set has an even number of \"inversions\"; the other has an odd number. An inversion is when a piece in the state is larger than a piece that follows it.\n",
    "\n",
    "\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 397,
   "metadata": {},
   "outputs": [],
   "source": [
    "class EightPuzzle(Problem):\n",
    "    \"\"\" The problem of sliding tiles numbered from 1 to 8 on a 3x3 board,\n",
    "    where one of the squares is a blank, trying to reach a goal configuration.\n",
    "    A board state is represented as a tuple of length 9, where the element at index i \n",
    "    represents the tile number at index i, or 0 if for the empty square, e.g. the goal:\n",
    "        1 2 3\n",
    "        4 5 6 ==> (1, 2, 3, 4, 5, 6, 7, 8, 0)\n",
    "        7 8 _\n",
    "    \"\"\"\n",
    "\n",
    "    def __init__(self, initial, goal=(0, 1, 2, 3, 4, 5, 6, 7, 8)):\n",
    "        assert inversions(initial) % 2 == inversions(goal) % 2 # Parity check\n",
    "        self.initial, self.goal = initial, goal\n",
    "    \n",
    "    def actions(self, state):\n",
    "        \"\"\"The indexes of the squares that the blank can move to.\"\"\"\n",
    "        moves = ((1, 3),    (0, 2, 4),    (1, 5),\n",
    "                 (0, 4, 6), (1, 3, 5, 7), (2, 4, 8),\n",
    "                 (3, 7),    (4, 6, 8),    (7, 5))\n",
    "        blank = state.index(0)\n",
    "        return moves[blank]\n",
    "    \n",
    "    def result(self, state, action):\n",
    "        \"\"\"Swap the blank with the square numbered `action`.\"\"\"\n",
    "        s = list(state)\n",
    "        blank = state.index(0)\n",
    "        s[action], s[blank] = s[blank], s[action]\n",
    "        return tuple(s)\n",
    "    \n",
    "    def h1(self, node):\n",
    "        \"\"\"The misplaced tiles heuristic.\"\"\"\n",
    "        return hamming_distance(node.state, self.goal)\n",
    "    \n",
    "    def h2(self, node):\n",
    "        \"\"\"The Manhattan heuristic.\"\"\"\n",
    "        X = (0, 1, 2, 0, 1, 2, 0, 1, 2)\n",
    "        Y = (0, 0, 0, 1, 1, 1, 2, 2, 2)\n",
    "        return sum(abs(X[s] - X[g]) + abs(Y[s] - Y[g])\n",
    "                   for (s, g) in zip(node.state, self.goal) if s != 0)\n",
    "    \n",
    "    def h(self, node): return h2(self, node)\n",
    "    \n",
    "    \n",
    "def hamming_distance(A, B):\n",
    "    \"Number of positions where vectors A and B are different.\"\n",
    "    return sum(a != b for a, b in zip(A, B))\n",
    "    \n",
    "\n",
    "def inversions(board):\n",
    "    \"The number of times a piece is a smaller number than a following piece.\"\n",
    "    return sum((a > b and a != 0 and b != 0) for (a, b) in combinations(board, 2))\n",
    "    \n",
    "    \n",
    "def board8(board, fmt=(3 * '{} {} {}\\n')):\n",
    "    \"A string representing an 8-puzzle board\"\n",
    "    return fmt.format(*board).replace('0', '_')\n",
    "\n",
    "class Board(defaultdict):\n",
    "    empty = '.'\n",
    "    off = '#'\n",
    "    def __init__(self, board=None, width=8, height=8, to_move=None, **kwds):\n",
    "        if board is not None:\n",
    "            self.update(board)\n",
    "            self.width, self.height = (board.width, board.height) \n",
    "        else:\n",
    "            self.width, self.height = (width, height)\n",
    "        self.to_move = to_move\n",
    "\n",
    "    def __missing__(self, key):\n",
    "        x, y = key\n",
    "        if x < 0 or x >= self.width or y < 0 or y >= self.height:\n",
    "            return self.off\n",
    "        else:\n",
    "            return self.empty\n",
    "        \n",
    "    def __repr__(self):\n",
    "        def row(y): return ' '.join(self[x, y] for x in range(self.width))\n",
    "        return '\\n'.join(row(y) for y in range(self.height))\n",
    "            \n",
    "    def __hash__(self): \n",
    "        return hash(tuple(sorted(self.items()))) + hash(self.to_move)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 23,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Some specific EightPuzzle problems\n",
    "\n",
    "e1 = EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8))\n",
    "e2 = EightPuzzle((1, 2, 3, 4, 5, 6, 7, 8, 0))\n",
    "e3 = EightPuzzle((4, 0, 2, 5, 1, 3, 7, 8, 6))\n",
    "e4 = EightPuzzle((7, 2, 4, 5, 0, 6, 8, 3, 1))\n",
    "e5 = EightPuzzle((8, 6, 7, 2, 5, 4, 3, 0, 1))"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 24,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "1 4 2\n",
      "_ 7 5\n",
      "3 6 8\n",
      "\n",
      "1 4 2\n",
      "3 7 5\n",
      "_ 6 8\n",
      "\n",
      "1 4 2\n",
      "3 7 5\n",
      "6 _ 8\n",
      "\n",
      "1 4 2\n",
      "3 _ 5\n",
      "6 7 8\n",
      "\n",
      "1 _ 2\n",
      "3 4 5\n",
      "6 7 8\n",
      "\n",
      "_ 1 2\n",
      "3 4 5\n",
      "6 7 8\n",
      "\n"
     ]
    }
   ],
   "source": [
    "# Solve an 8 puzzle problem and print out each state\n",
    "\n",
    "for s in path_states(astar_search(e1)):\n",
    "    print(board8(s))"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Water Pouring Problems\n",
    "\n",
    "![](http://puzzles.nigelcoldwell.co.uk/images/water22.png)\n",
    "\n",
    "In a [water pouring problem](https://en.wikipedia.org/wiki/Water_pouring_puzzle) you are given a collection of jugs, each of which has a size (capacity) in, say, litres, and a current level of water (in litres). The goal is to measure out a certain level of water; it can appear in any of the jugs. For example, in the movie *Die Hard 3*, the heroes were faced with the task of making exactly 4 gallons from jugs of size 5 gallons and 3 gallons.) A state is represented by a tuple of current water levels, and the available actions are:\n",
    "- `(Fill, i)`: fill the `i`th jug all the way to the top (from a tap with unlimited water).\n",
    "- `(Dump, i)`: dump all the water out of the `i`th jug.\n",
    "- `(Pour, i, j)`: pour water from the `i`th jug into the `j`th jug until either the jug `i` is empty, or jug `j` is full, whichever comes first."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 25,
   "metadata": {},
   "outputs": [],
   "source": [
    "class PourProblem(Problem):\n",
    "    \"\"\"Problem about pouring water between jugs to achieve some water level.\n",
    "    Each state is a tuples of water levels. In the initialization, also provide a tuple of \n",
    "    jug sizes, e.g. PourProblem(initial=(0, 0), goal=4, sizes=(5, 3)), \n",
    "    which means two jugs of sizes 5 and 3, initially both empty, with the goal\n",
    "    of getting a level of 4 in either jug.\"\"\"\n",
    "    \n",
    "    def actions(self, state):\n",
    "        \"\"\"The actions executable in this state.\"\"\"\n",
    "        jugs = range(len(state))\n",
    "        return ([('Fill', i)    for i in jugs if state[i] < self.sizes[i]] +\n",
    "                [('Dump', i)    for i in jugs if state[i]] +\n",
    "                [('Pour', i, j) for i in jugs if state[i] for j in jugs if i != j])\n",
    "\n",
    "    def result(self, state, action):\n",
    "        \"\"\"The state that results from executing this action in this state.\"\"\"\n",
    "        result = list(state)\n",
    "        act, i, *_ = action\n",
    "        if act == 'Fill':   # Fill i to capacity\n",
    "            result[i] = self.sizes[i]\n",
    "        elif act == 'Dump': # Empty i\n",
    "            result[i] = 0\n",
    "        elif act == 'Pour': # Pour from i into j\n",
    "            j = action[2]\n",
    "            amount = min(state[i], self.sizes[j] - state[j])\n",
    "            result[i] -= amount\n",
    "            result[j] += amount\n",
    "        return tuple(result)\n",
    "\n",
    "    def is_goal(self, state):\n",
    "        \"\"\"True if the goal level is in any one of the jugs.\"\"\"\n",
    "        return self.goal in state"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "In a `GreenPourProblem`, the states and actions are the same, but instead of all actions costing 1, in these problems the cost of an action is the amount of water that flows from the tap. (There is an issue that non-*Fill* actions have 0 cost, which in general can lead to indefinitely long solutions, but in this problem there is a finite number of states, so we're ok.)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 26,
   "metadata": {},
   "outputs": [],
   "source": [
    "class GreenPourProblem(PourProblem): \n",
    "    \"\"\"A PourProblem in which the cost is the amount of water used.\"\"\"\n",
    "    def action_cost(self, s, action, s1):\n",
    "        \"The cost is the amount of water used.\"\n",
    "        act, i, *_ = action\n",
    "        return self.sizes[i] - s[i] if act == 'Fill' else 0"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 27,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Some specific PourProblems\n",
    "\n",
    "p1 = PourProblem((1, 1, 1), 13, sizes=(2, 16, 32))\n",
    "p2 = PourProblem((0, 0, 0), 21, sizes=(8, 11, 31))\n",
    "p3 = PourProblem((0, 0),     8, sizes=(7,9))\n",
    "p4 = PourProblem((0, 0, 0), 21, sizes=(8, 11, 31))\n",
    "p5 = PourProblem((0, 0),     4, sizes=(3, 5))\n",
    "\n",
    "g1 = GreenPourProblem((1, 1, 1), 13, sizes=(2, 16, 32))\n",
    "g2 = GreenPourProblem((0, 0, 0), 21, sizes=(8, 11, 31))\n",
    "g3 = GreenPourProblem((0, 0),     8, sizes=(7,9))\n",
    "g4 = GreenPourProblem((0, 0, 0), 21, sizes=(8, 11, 31))\n",
    "g5 = GreenPourProblem((0, 0),     4, sizes=(3, 5))"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 28,
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "([('Fill', 1), ('Pour', 1, 0), ('Dump', 0), ('Pour', 1, 0)],\n",
       " [(1, 1, 1), (1, 16, 1), (2, 15, 1), (0, 15, 1), (2, 13, 1)])"
      ]
     },
     "execution_count": 28,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "# Solve the PourProblem of getting 13 in some jug, and show the actions and states\n",
    "soln = breadth_first_search(p1)\n",
    "path_actions(soln), path_states(soln)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Pancake Sorting Problems\n",
    "\n",
    "Given a stack of pancakes of various sizes, can you sort them into a stack of decreasing sizes, largest on bottom to smallest on top? You have a spatula with which you can flip the top `i` pancakes. This is shown below for `i = 3`; on the top the spatula grabs the first three pancakes; on the bottom we see them flipped:\n",
    "\n",
    "\n",
    "![](https://upload.wikimedia.org/wikipedia/commons/0/0f/Pancake_sort_operation.png)\n",
    "\n",
    "How many flips will it take to get the whole stack sorted? This is an interesting [problem](https://en.wikipedia.org/wiki/Pancake_sorting) that Bill Gates has [written about](https://people.eecs.berkeley.edu/~christos/papers/Bounds%20For%20Sorting%20By%20Prefix%20Reversal.pdf). A reasonable heuristic for this problem is the *gap heuristic*: if we look at neighboring pancakes, if, say, the 2nd smallest is next to the 3rd smallest, that's good; they should stay next to each other. But if the 2nd smallest is next to the 4th smallest, that's bad: we will require at least one move to separate them and insert the 3rd smallest between them. The gap heuristic counts the number of neighbors that have a gap like this. In our specification of the problem, pancakes are ranked by size: the smallest is `1`, the 2nd smallest `2`, and so on, and the representation of a state is a tuple of these rankings, from the top to the bottom pancake. Thus the goal state is always `(1, 2, ..., `*n*`)` and the initial (top) state in the diagram above is `(2, 1, 4, 6, 3, 5)`.\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 29,
   "metadata": {},
   "outputs": [],
   "source": [
    "class PancakeProblem(Problem):\n",
    "    \"\"\"A PancakeProblem the goal is always `tuple(range(1, n+1))`, where the\n",
    "    initial state is a permutation of `range(1, n+1)`. An act is the index `i` \n",
    "    of the top `i` pancakes that will be flipped.\"\"\"\n",
    "    \n",
    "    def __init__(self, initial): \n",
    "        self.initial, self.goal = tuple(initial), tuple(sorted(initial))\n",
    "    \n",
    "    def actions(self, state): return range(2, len(state) + 1)\n",
    "\n",
    "    def result(self, state, i): return state[:i][::-1] + state[i:]\n",
    "    \n",
    "    def h(self, node):\n",
    "        \"The gap heuristic.\"\n",
    "        s = node.state\n",
    "        return sum(abs(s[i] - s[i - 1]) > 1 for i in range(1, len(s)))"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 30,
   "metadata": {},
   "outputs": [],
   "source": [
    "c0 = PancakeProblem((2, 1, 4, 6, 3, 5))\n",
    "c1 = PancakeProblem((4, 6, 2, 5, 1, 3))\n",
    "c2 = PancakeProblem((1, 3, 7, 5, 2, 6, 4))\n",
    "c3 = PancakeProblem((1, 7, 2, 6, 3, 5, 4))\n",
    "c4 = PancakeProblem((1, 3, 5, 7, 9, 2, 4, 6, 8))"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 31,
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "[(2, 1, 4, 6, 3, 5),\n",
       " (6, 4, 1, 2, 3, 5),\n",
       " (5, 3, 2, 1, 4, 6),\n",
       " (4, 1, 2, 3, 5, 6),\n",
       " (3, 2, 1, 4, 5, 6),\n",
       " (1, 2, 3, 4, 5, 6)]"
      ]
     },
     "execution_count": 31,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "# Solve a pancake problem\n",
    "path_states(astar_search(c0))"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Jumping Frogs Puzzle\n",
    "\n",
    "In this puzzle (which also can be played as a two-player game), the initial state is a line of squares, with N pieces of one kind on the left, then one empty square, then N pieces of another kind on the right. The diagram below uses 2 blue toads and 2 red frogs; we will represent this as the string `'LL.RR'`. The goal is to swap the pieces, arriving at `'RR.LL'`. An `'L'` piece moves left-to-right, either sliding one space ahead to an empty space, or two spaces ahead if that space is empty and if there is an `'R'` in between to hop over. The `'R'` pieces move right-to-left analogously. An action will be an `(i, j)` pair meaning to swap the pieces at those indexes. The set of actions for the N = 2 position below is `{(1, 2), (3, 2)}`, meaning either the blue toad in position 1 or the red frog in position 3 can swap places with the blank in position 2.\n",
    "\n",
    "![](https://upload.wikimedia.org/wikipedia/commons/2/2f/ToadsAndFrogs.png)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 32,
   "metadata": {},
   "outputs": [],
   "source": [
    "class JumpingPuzzle(Problem):\n",
    "    \"\"\"Try to exchange L and R by moving one ahead or hopping two ahead.\"\"\"\n",
    "    def __init__(self, N=2):\n",
    "        self.initial = N*'L' + '.' + N*'R'\n",
    "        self.goal = self.initial[::-1]\n",
    "        \n",
    "    def actions(self, state):\n",
    "        \"\"\"Find all possible move or hop moves.\"\"\"\n",
    "        idxs = range(len(state))\n",
    "        return ({(i, i + 1) for i in idxs if state[i:i+2] == 'L.'}   # Slide\n",
    "               |{(i, i + 2) for i in idxs if state[i:i+3] == 'LR.'}  # Hop\n",
    "               |{(i + 1, i) for i in idxs if state[i:i+2] == '.R'}   # Slide\n",
    "               |{(i + 2, i) for i in idxs if state[i:i+3] == '.LR'}) # Hop\n",
    "\n",
    "    def result(self, state, action):\n",
    "        \"\"\"An action (i, j) means swap the pieces at positions i and j.\"\"\"\n",
    "        i, j = action\n",
    "        result = list(state)\n",
    "        result[i], result[j] = state[j], state[i]\n",
    "        return ''.join(result)\n",
    "    \n",
    "    def h(self, node): return hamming_distance(node.state, self.goal)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 33,
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "{(1, 2), (3, 2)}"
      ]
     },
     "execution_count": 33,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "JumpingPuzzle(N=2).actions('LL.RR')"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 34,
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "['LLL.RRR',\n",
       " 'LLLR.RR',\n",
       " 'LL.RLRR',\n",
       " 'L.LRLRR',\n",
       " 'LRL.LRR',\n",
       " 'LRLRL.R',\n",
       " 'LRLRLR.',\n",
       " 'LRLR.RL',\n",
       " 'LR.RLRL',\n",
       " '.RLRLRL',\n",
       " 'R.LRLRL',\n",
       " 'RRL.LRL',\n",
       " 'RRLRL.L',\n",
       " 'RRLR.LL',\n",
       " 'RR.RLLL',\n",
       " 'RRR.LLL']"
      ]
     },
     "execution_count": 34,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "j3 = JumpingPuzzle(N=3)\n",
    "j9 = JumpingPuzzle(N=9)\n",
    "path_states(astar_search(j3))"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Reporting Summary Statistics on Search Algorithms\n",
    "\n",
    "Now let's gather some metrics on how well each algorithm does.  We'll use `CountCalls` to wrap a `Problem` object in such a way that calls to its methods are delegated to the original problem, but each call increments a counter. Once we've solved the problem, we print out summary statistics."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 35,
   "metadata": {},
   "outputs": [],
   "source": [
    "class CountCalls:\n",
    "    \"\"\"Delegate all attribute gets to the object, and count them in ._counts\"\"\"\n",
    "    def __init__(self, obj):\n",
    "        self._object = obj\n",
    "        self._counts = Counter()\n",
    "        \n",
    "    def __getattr__(self, attr):\n",
    "        \"Delegate to the original object, after incrementing a counter.\"\n",
    "        self._counts[attr] += 1\n",
    "        return getattr(self._object, attr)\n",
    "\n",
    "        \n",
    "def report(searchers, problems, verbose=True):\n",
    "    \"\"\"Show summary statistics for each searcher (and on each problem unless verbose is false).\"\"\"\n",
    "    for searcher in searchers:\n",
    "        print(searcher.__name__ + ':')\n",
    "        total_counts = Counter()\n",
    "        for p in problems:\n",
    "            prob   = CountCalls(p)\n",
    "            soln   = searcher(prob)\n",
    "            counts = prob._counts; \n",
    "            counts.update(actions=len(soln), cost=soln.path_cost)\n",
    "            total_counts += counts\n",
    "            if verbose: report_counts(counts, str(p)[:40])\n",
    "        report_counts(total_counts, 'TOTAL\\n')\n",
    "        \n",
    "def report_counts(counts, name):\n",
    "    \"\"\"Print one line of the counts report.\"\"\"\n",
    "    print('{:9,d} nodes |{:9,d} goal |{:5.0f} cost |{:8,d} actions | {}'.format(\n",
    "          counts['result'], counts['is_goal'], counts['cost'], counts['actions'], name))"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Here's a tiny report for uniform-cost search on the jug pouring problems:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 36,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "uniform_cost_search:\n",
      "      948 nodes |      109 goal |    4 cost |     112 actions | PourProblem((1, 1, 1), 13)\n",
      "    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)\n",
      "      124 nodes |       30 goal |   14 cost |      43 actions | PourProblem((0, 0), 8)\n",
      "    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)\n",
      "       52 nodes |       14 goal |    6 cost |      19 actions | PourProblem((0, 0), 4)\n",
      "    8,122 nodes |      931 goal |   42 cost |     968 actions | TOTAL\n",
      "\n"
     ]
    }
   ],
   "source": [
    "report([uniform_cost_search], [p1, p2, p3, p4, p5])"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 37,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "uniform_cost_search:\n",
      "      948 nodes |      109 goal |    4 cost |     112 actions | PourProblem((1, 1, 1), 13)\n",
      "    1,696 nodes |      190 goal |   10 cost |     204 actions | GreenPourProblem((1, 1, 1), 13)\n",
      "    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)\n",
      "    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "      124 nodes |       30 goal |   14 cost |      43 actions | PourProblem((0, 0), 8)\n",
      "      124 nodes |       30 goal |   35 cost |      45 actions | GreenPourProblem((0, 0), 8)\n",
      "    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)\n",
      "    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)\n",
      "    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "    3,590 nodes |      719 goal |    7 cost |     725 actions | PancakeProblem((4, 6, 2, 5, 1, 3), (1, 2\n",
      "   30,204 nodes |    5,035 goal |    8 cost |   5,042 actions | PancakeProblem((1, 3, 7, 5, 2, 6, 4), (1\n",
      "   22,068 nodes |    3,679 goal |    6 cost |   3,684 actions | PancakeProblem((1, 7, 2, 6, 3, 5, 4), (1\n",
      "   81,467 nodes |   12,321 goal |  174 cost |  12,435 actions | TOTAL\n",
      "\n",
      "breadth_first_search:\n",
      "      596 nodes |      597 goal |    4 cost |      73 actions | PourProblem((1, 1, 1), 13)\n",
      "      596 nodes |      597 goal |   15 cost |      73 actions | GreenPourProblem((1, 1, 1), 13)\n",
      "    2,618 nodes |    2,619 goal |    9 cost |     302 actions | PourProblem((0, 0, 0), 21)\n",
      "    2,618 nodes |    2,619 goal |   32 cost |     302 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "      120 nodes |      121 goal |   14 cost |      42 actions | PourProblem((0, 0), 8)\n",
      "      120 nodes |      121 goal |   36 cost |      42 actions | GreenPourProblem((0, 0), 8)\n",
      "    2,618 nodes |    2,619 goal |    9 cost |     302 actions | PourProblem((0, 0, 0), 21)\n",
      "    2,618 nodes |    2,619 goal |   32 cost |     302 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "    2,618 nodes |    2,619 goal |    9 cost |     302 actions | PourProblem((0, 0, 0), 21)\n",
      "    2,618 nodes |    2,619 goal |   32 cost |     302 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "    2,951 nodes |    2,952 goal |    7 cost |     598 actions | PancakeProblem((4, 6, 2, 5, 1, 3), (1, 2\n",
      "   25,945 nodes |   25,946 goal |    8 cost |   4,333 actions | PancakeProblem((1, 3, 7, 5, 2, 6, 4), (1\n",
      "    5,975 nodes |    5,976 goal |    6 cost |   1,002 actions | PancakeProblem((1, 7, 2, 6, 3, 5, 4), (1\n",
      "   52,011 nodes |   52,024 goal |  213 cost |   7,975 actions | TOTAL\n",
      "\n"
     ]
    }
   ],
   "source": [
    "report((uniform_cost_search, breadth_first_search), \n",
    "       (p1, g1, p2, g2, p3, g3, p4, g4, p4, g4, c1, c2, c3)) "
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Comparing heuristics\n",
    "\n",
    "First, let's look at the eight puzzle problems, and compare three different heuristics the Manhattan heuristic, the less informative misplaced tiles heuristic, and the uninformed (i.e. *h* = 0) breadth-first search:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 38,
   "metadata": {
    "scrolled": false
   },
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "breadth_first_search:\n",
      "       81 nodes |       82 goal |    5 cost |      35 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "  160,948 nodes |  160,949 goal |   22 cost |  59,960 actions | EightPuzzle((1, 2, 3, 4, 5, 6, 7, 8, 0),\n",
      "  218,263 nodes |  218,264 goal |   23 cost |  81,829 actions | EightPuzzle((4, 0, 2, 5, 1, 3, 7, 8, 6),\n",
      "  418,771 nodes |  418,772 goal |   26 cost | 156,533 actions | EightPuzzle((7, 2, 4, 5, 0, 6, 8, 3, 1),\n",
      "  448,667 nodes |  448,668 goal |   27 cost | 167,799 actions | EightPuzzle((8, 6, 7, 2, 5, 4, 3, 0, 1),\n",
      "1,246,730 nodes |1,246,735 goal |  103 cost | 466,156 actions | TOTAL\n",
      "\n",
      "astar_misplaced_tiles:\n",
      "       17 nodes |        7 goal |    5 cost |      11 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "   23,407 nodes |    8,726 goal |   22 cost |   8,747 actions | EightPuzzle((1, 2, 3, 4, 5, 6, 7, 8, 0),\n",
      "   38,632 nodes |   14,433 goal |   23 cost |  14,455 actions | EightPuzzle((4, 0, 2, 5, 1, 3, 7, 8, 6),\n",
      "  124,324 nodes |   46,553 goal |   26 cost |  46,578 actions | EightPuzzle((7, 2, 4, 5, 0, 6, 8, 3, 1),\n",
      "  156,111 nodes |   58,475 goal |   27 cost |  58,501 actions | EightPuzzle((8, 6, 7, 2, 5, 4, 3, 0, 1),\n",
      "  342,491 nodes |  128,194 goal |  103 cost | 128,292 actions | TOTAL\n",
      "\n",
      "astar_search:\n",
      "       15 nodes |        6 goal |    5 cost |      10 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "    3,614 nodes |    1,349 goal |   22 cost |   1,370 actions | EightPuzzle((1, 2, 3, 4, 5, 6, 7, 8, 0),\n",
      "    5,373 nodes |    2,010 goal |   23 cost |   2,032 actions | EightPuzzle((4, 0, 2, 5, 1, 3, 7, 8, 6),\n",
      "   10,832 nodes |    4,086 goal |   26 cost |   4,111 actions | EightPuzzle((7, 2, 4, 5, 0, 6, 8, 3, 1),\n",
      "   11,669 nodes |    4,417 goal |   27 cost |   4,443 actions | EightPuzzle((8, 6, 7, 2, 5, 4, 3, 0, 1),\n",
      "   31,503 nodes |   11,868 goal |  103 cost |  11,966 actions | TOTAL\n",
      "\n"
     ]
    }
   ],
   "source": [
    "def astar_misplaced_tiles(problem): return astar_search(problem, h=problem.h1)\n",
    "\n",
    "report([breadth_first_search, astar_misplaced_tiles, astar_search], \n",
    "       [e1, e2, e3, e4, e5])"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "We see that all three algorithms get cost-optimal solutions, but the better the heuristic, the fewer nodes explored. \n",
    "Compared to the uninformed search, the misplaced tiles heuristic explores about 1/4 the number of nodes, and the Manhattan heuristic needs just 2%.\n",
    "\n",
    "Next, we can show the value of the gap heuristic for pancake sorting problems:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 39,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "astar_search:\n",
      "    1,285 nodes |      258 goal |    7 cost |     264 actions | PancakeProblem((4, 6, 2, 5, 1, 3), (1, 2\n",
      "    3,804 nodes |      635 goal |    8 cost |     642 actions | PancakeProblem((1, 3, 7, 5, 2, 6, 4), (1\n",
      "      294 nodes |       50 goal |    6 cost |      55 actions | PancakeProblem((1, 7, 2, 6, 3, 5, 4), (1\n",
      "    2,256 nodes |      283 goal |    9 cost |     291 actions | PancakeProblem((1, 3, 5, 7, 9, 2, 4, 6, \n",
      "    7,639 nodes |    1,226 goal |   30 cost |   1,252 actions | TOTAL\n",
      "\n",
      "uniform_cost_search:\n",
      "    3,590 nodes |      719 goal |    7 cost |     725 actions | PancakeProblem((4, 6, 2, 5, 1, 3), (1, 2\n",
      "   30,204 nodes |    5,035 goal |    8 cost |   5,042 actions | PancakeProblem((1, 3, 7, 5, 2, 6, 4), (1\n",
      "   22,068 nodes |    3,679 goal |    6 cost |   3,684 actions | PancakeProblem((1, 7, 2, 6, 3, 5, 4), (1\n",
      "2,271,792 nodes |  283,975 goal |    9 cost | 283,983 actions | PancakeProblem((1, 3, 5, 7, 9, 2, 4, 6, \n",
      "2,327,654 nodes |  293,408 goal |   30 cost | 293,434 actions | TOTAL\n",
      "\n"
     ]
    }
   ],
   "source": [
    "report([astar_search, uniform_cost_search], [c1, c2, c3, c4])"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "We need to explore 300 times more nodes without the heuristic.\n",
    "\n",
    "# Comparing graph search and tree search\n",
    "\n",
    "Keeping the *reached* table in `best_first_search` allows us to do a graph search, where we notice when we reach a state by two different paths, rather than a tree search, where we have duplicated effort. The *reached* table consumes space and also saves time. How much time? In part it depends on how good the heuristics are at focusing the search.  Below we show that on some pancake and eight puzzle problems, the tree search expands roughly twice as many nodes (and thus takes roughly twice as much time):"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 188,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "astar_search:\n",
      "       15 nodes |        6 goal |    5 cost |      10 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "    3,614 nodes |    1,349 goal |   22 cost |   1,370 actions | EightPuzzle((1, 2, 3, 4, 5, 6, 7, 8, 0),\n",
      "    5,373 nodes |    2,010 goal |   23 cost |   2,032 actions | EightPuzzle((4, 0, 2, 5, 1, 3, 7, 8, 6),\n",
      "   10,832 nodes |    4,086 goal |   26 cost |   4,111 actions | EightPuzzle((7, 2, 4, 5, 0, 6, 8, 3, 1),\n",
      "       15 nodes |        6 goal |  418 cost |       9 actions | RouteProblem('A', 'B')\n",
      "       34 nodes |       15 goal |  910 cost |      23 actions | RouteProblem('N', 'L')\n",
      "       33 nodes |       14 goal |  805 cost |      21 actions | RouteProblem('E', 'T')\n",
      "       20 nodes |        9 goal |  445 cost |      13 actions | RouteProblem('O', 'M')\n",
      "   19,936 nodes |    7,495 goal | 2654 cost |   7,589 actions | TOTAL\n",
      "\n",
      "astar_tree_search:\n",
      "       15 nodes |        6 goal |    5 cost |      10 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "    5,384 nodes |    2,000 goal |   22 cost |   2,021 actions | EightPuzzle((1, 2, 3, 4, 5, 6, 7, 8, 0),\n",
      "    9,116 nodes |    3,404 goal |   23 cost |   3,426 actions | EightPuzzle((4, 0, 2, 5, 1, 3, 7, 8, 6),\n",
      "   19,084 nodes |    7,185 goal |   26 cost |   7,210 actions | EightPuzzle((7, 2, 4, 5, 0, 6, 8, 3, 1),\n",
      "       15 nodes |        6 goal |  418 cost |       9 actions | RouteProblem('A', 'B')\n",
      "       47 nodes |       19 goal |  910 cost |      27 actions | RouteProblem('N', 'L')\n",
      "       46 nodes |       18 goal |  805 cost |      25 actions | RouteProblem('E', 'T')\n",
      "       24 nodes |       10 goal |  445 cost |      14 actions | RouteProblem('O', 'M')\n",
      "   33,731 nodes |   12,648 goal | 2654 cost |  12,742 actions | TOTAL\n",
      "\n"
     ]
    }
   ],
   "source": [
    "report([astar_search, astar_tree_search], [e1, e2, e3, e4, r1, r2, r3, r4])"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Comparing different weighted search values\n",
    "\n",
    "Below we report on problems using these four algorithms:\n",
    "\n",
    "|Algorithm|*f*|Optimality|\n",
    "|:---------|---:|:----------:|\n",
    "|Greedy best-first search | *f = h*|nonoptimal|\n",
    "|Extra weighted A* search | *f = g + 2 &times; h*|nonoptimal|\n",
    "|Weighted A* search | *f = g + 1.4 &times; h*|nonoptimal|\n",
    "|A* search | *f = g + h*|optimal|\n",
    "|Uniform-cost search | *f = g*|optimal|\n",
    "\n",
    "We will see that greedy best-first search (which ranks nodes solely by the heuristic) explores the fewest number of nodes, but has the highest path costs. Weighted A* search explores twice as many nodes (on this problem set) but gets 10% better path costs. A* is optimal, but explores more nodes, and uniform-cost is also optimal, but explores an order of magnitude more nodes."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 41,
   "metadata": {
    "scrolled": false
   },
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "greedy_bfs:\n",
      "        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')\n",
      "        9 nodes |        4 goal |  450 cost |       6 actions | RouteProblem('A', 'B')\n",
      "       29 nodes |       12 goal |  910 cost |      20 actions | RouteProblem('N', 'L')\n",
      "       19 nodes |        8 goal |  837 cost |      14 actions | RouteProblem('E', 'T')\n",
      "       14 nodes |        6 goal |  572 cost |      10 actions | RouteProblem('O', 'M')\n",
      "       15 nodes |        6 goal |    5 cost |      10 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "      909 nodes |      138 goal |  136 cost |     258 actions | GridProblem((15, 30), (130, 30))\n",
      "      974 nodes |      147 goal |  152 cost |     277 actions | GridProblem((15, 30), (130, 30))\n",
      "    5,146 nodes |    4,984 goal |   99 cost |   5,082 actions | JumpingPuzzle('LLLLLLLLL.RRRRRRRRR', 'RR\n",
      "    1,569 nodes |      568 goal |   58 cost |     625 actions | EightPuzzle((1, 2, 3, 4, 5, 6, 7, 8, 0),\n",
      "    1,424 nodes |      257 goal |  164 cost |     406 actions | GridProblem((15, 30), (130, 30))\n",
      "    1,899 nodes |      342 goal |  153 cost |     470 actions | GridProblem((15, 30), (130, 30))\n",
      "   18,239 nodes |    2,439 goal |  134 cost |   2,564 actions | GridProblem((15, 30), (130, 30))\n",
      "   18,329 nodes |    2,460 goal |  152 cost |   2,594 actions | GridProblem((15, 30), (130, 30))\n",
      "      287 nodes |      109 goal |   33 cost |     141 actions | EightPuzzle((4, 0, 2, 5, 1, 3, 7, 8, 6),\n",
      "    1,128 nodes |      408 goal |   46 cost |     453 actions | EightPuzzle((7, 2, 4, 5, 0, 6, 8, 3, 1),\n",
      "   49,990 nodes |   11,889 goal | 3901 cost |  12,930 actions | TOTAL\n",
      "\n",
      "extra_weighted_astar_search:\n",
      "        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')\n",
      "        9 nodes |        4 goal |  450 cost |       6 actions | RouteProblem('A', 'B')\n",
      "       29 nodes |       12 goal |  910 cost |      20 actions | RouteProblem('N', 'L')\n",
      "       23 nodes |        9 goal |  805 cost |      16 actions | RouteProblem('E', 'T')\n",
      "       18 nodes |        8 goal |  445 cost |      12 actions | RouteProblem('O', 'M')\n",
      "       15 nodes |        6 goal |    5 cost |      10 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "    1,575 nodes |      239 goal |  136 cost |     357 actions | GridProblem((15, 30), (130, 30))\n",
      "    1,384 nodes |      231 goal |  133 cost |     349 actions | GridProblem((15, 30), (130, 30))\n",
      "   10,990 nodes |   10,660 goal |   99 cost |  10,758 actions | JumpingPuzzle('LLLLLLLLL.RRRRRRRRR', 'RR\n",
      "    1,720 nodes |      633 goal |   24 cost |     656 actions | EightPuzzle((1, 2, 3, 4, 5, 6, 7, 8, 0),\n",
      "    9,282 nodes |    1,412 goal |  163 cost |   1,551 actions | GridProblem((15, 30), (130, 30))\n",
      "    1,354 nodes |      228 goal |  134 cost |     345 actions | GridProblem((15, 30), (130, 30))\n",
      "   16,024 nodes |    2,098 goal |  129 cost |   2,214 actions | GridProblem((15, 30), (130, 30))\n",
      "   16,950 nodes |    2,237 goal |  140 cost |   2,359 actions | GridProblem((15, 30), (130, 30))\n",
      "    1,908 nodes |      709 goal |   25 cost |     733 actions | EightPuzzle((4, 0, 2, 5, 1, 3, 7, 8, 6),\n",
      "    1,312 nodes |      489 goal |   30 cost |     518 actions | EightPuzzle((7, 2, 4, 5, 0, 6, 8, 3, 1),\n",
      "   62,593 nodes |   18,976 goal | 3628 cost |  19,904 actions | TOTAL\n",
      "\n",
      "weighted_astar_search:\n",
      "        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')\n",
      "        9 nodes |        4 goal |  450 cost |       6 actions | RouteProblem('A', 'B')\n",
      "       32 nodes |       14 goal |  910 cost |      22 actions | RouteProblem('N', 'L')\n",
      "       29 nodes |       12 goal |  805 cost |      19 actions | RouteProblem('E', 'T')\n",
      "       18 nodes |        8 goal |  445 cost |      12 actions | RouteProblem('O', 'M')\n",
      "       15 nodes |        6 goal |    5 cost |      10 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "    1,631 nodes |      236 goal |  128 cost |     350 actions | GridProblem((15, 30), (130, 30))\n",
      "    1,706 nodes |      275 goal |  131 cost |     389 actions | GridProblem((15, 30), (130, 30))\n",
      "   10,990 nodes |   10,660 goal |   99 cost |  10,758 actions | JumpingPuzzle('LLLLLLLLL.RRRRRRRRR', 'RR\n",
      "    2,082 nodes |      771 goal |   22 cost |     792 actions | EightPuzzle((1, 2, 3, 4, 5, 6, 7, 8, 0),\n",
      "    8,385 nodes |    1,266 goal |  154 cost |   1,396 actions | GridProblem((15, 30), (130, 30))\n",
      "    1,400 nodes |      229 goal |  133 cost |     344 actions | GridProblem((15, 30), (130, 30))\n",
      "   12,122 nodes |    1,572 goal |  124 cost |   1,686 actions | GridProblem((15, 30), (130, 30))\n",
      "   24,129 nodes |    3,141 goal |  127 cost |   3,255 actions | GridProblem((15, 30), (130, 30))\n",
      "    3,960 nodes |    1,475 goal |   25 cost |   1,499 actions | EightPuzzle((4, 0, 2, 5, 1, 3, 7, 8, 6),\n",
      "    1,992 nodes |      748 goal |   26 cost |     773 actions | EightPuzzle((7, 2, 4, 5, 0, 6, 8, 3, 1),\n",
      "   68,500 nodes |   20,418 goal | 3585 cost |  21,311 actions | TOTAL\n",
      "\n",
      "astar_search:\n",
      "        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')\n",
      "       15 nodes |        6 goal |  418 cost |       9 actions | RouteProblem('A', 'B')\n",
      "       34 nodes |       15 goal |  910 cost |      23 actions | RouteProblem('N', 'L')\n",
      "       33 nodes |       14 goal |  805 cost |      21 actions | RouteProblem('E', 'T')\n",
      "       20 nodes |        9 goal |  445 cost |      13 actions | RouteProblem('O', 'M')\n",
      "       15 nodes |        6 goal |    5 cost |      10 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "   26,711 nodes |    3,620 goal |  127 cost |   3,734 actions | GridProblem((15, 30), (130, 30))\n",
      "   12,932 nodes |    1,822 goal |  124 cost |   1,936 actions | GridProblem((15, 30), (130, 30))\n",
      "   10,991 nodes |   10,661 goal |   99 cost |  10,759 actions | JumpingPuzzle('LLLLLLLLL.RRRRRRRRR', 'RR\n",
      "    3,614 nodes |    1,349 goal |   22 cost |   1,370 actions | EightPuzzle((1, 2, 3, 4, 5, 6, 7, 8, 0),\n",
      "   62,509 nodes |    8,729 goal |  154 cost |   8,859 actions | GridProblem((15, 30), (130, 30))\n",
      "   15,190 nodes |    2,276 goal |  133 cost |   2,391 actions | GridProblem((15, 30), (130, 30))\n",
      "   25,303 nodes |    3,196 goal |  124 cost |   3,310 actions | GridProblem((15, 30), (130, 30))\n",
      "   32,572 nodes |    4,149 goal |  127 cost |   4,263 actions | GridProblem((15, 30), (130, 30))\n",
      "    5,373 nodes |    2,010 goal |   23 cost |   2,032 actions | EightPuzzle((4, 0, 2, 5, 1, 3, 7, 8, 6),\n",
      "   10,832 nodes |    4,086 goal |   26 cost |   4,111 actions | EightPuzzle((7, 2, 4, 5, 0, 6, 8, 3, 1),\n",
      "  206,144 nodes |   41,949 goal | 3543 cost |  42,841 actions | TOTAL\n",
      "\n",
      "uniform_cost_search:\n",
      "        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')\n",
      "       30 nodes |       13 goal |  418 cost |      16 actions | RouteProblem('A', 'B')\n",
      "       42 nodes |       19 goal |  910 cost |      27 actions | RouteProblem('N', 'L')\n",
      "       44 nodes |       20 goal |  805 cost |      27 actions | RouteProblem('E', 'T')\n",
      "       30 nodes |       12 goal |  445 cost |      16 actions | RouteProblem('O', 'M')\n",
      "      124 nodes |       46 goal |    5 cost |      50 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "  355,452 nodes |   44,984 goal |  127 cost |  45,098 actions | GridProblem((15, 30), (130, 30))\n",
      "  326,962 nodes |   41,650 goal |  124 cost |  41,764 actions | GridProblem((15, 30), (130, 30))\n",
      "   10,992 nodes |   10,662 goal |   99 cost |  10,760 actions | JumpingPuzzle('LLLLLLLLL.RRRRRRRRR', 'RR\n",
      "  214,952 nodes |   79,187 goal |   22 cost |  79,208 actions | EightPuzzle((1, 2, 3, 4, 5, 6, 7, 8, 0),\n",
      "  558,084 nodes |   70,738 goal |  154 cost |  70,868 actions | GridProblem((15, 30), (130, 30))\n",
      "  370,370 nodes |   47,243 goal |  133 cost |  47,358 actions | GridProblem((15, 30), (130, 30))\n",
      "  349,062 nodes |   43,693 goal |  124 cost |  43,807 actions | GridProblem((15, 30), (130, 30))\n",
      "  366,996 nodes |   45,970 goal |  127 cost |  46,084 actions | GridProblem((15, 30), (130, 30))\n",
      "  300,925 nodes |  112,082 goal |   23 cost | 112,104 actions | EightPuzzle((4, 0, 2, 5, 1, 3, 7, 8, 6),\n",
      "  457,766 nodes |  171,571 goal |   26 cost | 171,596 actions | EightPuzzle((7, 2, 4, 5, 0, 6, 8, 3, 1),\n",
      "3,311,831 nodes |  667,891 goal | 3543 cost | 668,783 actions | TOTAL\n",
      "\n"
     ]
    }
   ],
   "source": [
    "def extra_weighted_astar_search(problem): return weighted_astar_search(problem, weight=2)\n",
    "    \n",
    "report((greedy_bfs, extra_weighted_astar_search, weighted_astar_search, astar_search, uniform_cost_search), \n",
    "       (r0, r1, r2, r3, r4, e1, d1, d2, j9, e2, d3, d4, d6, d7, e3, e4))"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "We see that greedy search expands the fewest nodes, but has the highest path costs. In contrast, A\\* gets optimal path costs, but expands 4 or 5 times more nodes. Weighted A* is a good compromise, using half the compute time as A\\*, and achieving path costs within  1% or 2% of optimal. Uniform-cost is optimal, but is an order of magnitude slower than A\\*.\n",
    "\n",
    "# Comparing  many search algorithms\n",
    "\n",
    "Finally, we compare a host of algorihms (even the slow ones) on some of the easier problems:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 42,
   "metadata": {
    "scrolled": false
   },
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "astar_search:\n",
      "      948 nodes |      109 goal |    4 cost |     112 actions | PourProblem((1, 1, 1), 13)\n",
      "    1,696 nodes |      190 goal |   10 cost |     204 actions | GreenPourProblem((1, 1, 1), 13)\n",
      "    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)\n",
      "    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "      124 nodes |       30 goal |   14 cost |      43 actions | PourProblem((0, 0), 8)\n",
      "      124 nodes |       30 goal |   35 cost |      45 actions | GreenPourProblem((0, 0), 8)\n",
      "    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)\n",
      "    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')\n",
      "       15 nodes |        6 goal |  418 cost |       9 actions | RouteProblem('A', 'B')\n",
      "       34 nodes |       15 goal |  910 cost |      23 actions | RouteProblem('N', 'L')\n",
      "       33 nodes |       14 goal |  805 cost |      21 actions | RouteProblem('E', 'T')\n",
      "       20 nodes |        9 goal |  445 cost |      13 actions | RouteProblem('O', 'M')\n",
      "       15 nodes |        6 goal |    5 cost |      10 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "   18,151 nodes |    2,096 goal | 2706 cost |   2,200 actions | TOTAL\n",
      "\n",
      "uniform_cost_search:\n",
      "      948 nodes |      109 goal |    4 cost |     112 actions | PourProblem((1, 1, 1), 13)\n",
      "    1,696 nodes |      190 goal |   10 cost |     204 actions | GreenPourProblem((1, 1, 1), 13)\n",
      "    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)\n",
      "    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "      124 nodes |       30 goal |   14 cost |      43 actions | PourProblem((0, 0), 8)\n",
      "      124 nodes |       30 goal |   35 cost |      45 actions | GreenPourProblem((0, 0), 8)\n",
      "    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)\n",
      "    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')\n",
      "       30 nodes |       13 goal |  418 cost |      16 actions | RouteProblem('A', 'B')\n",
      "       42 nodes |       19 goal |  910 cost |      27 actions | RouteProblem('N', 'L')\n",
      "       44 nodes |       20 goal |  805 cost |      27 actions | RouteProblem('E', 'T')\n",
      "       30 nodes |       12 goal |  445 cost |      16 actions | RouteProblem('O', 'M')\n",
      "      124 nodes |       46 goal |    5 cost |      50 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "   18,304 nodes |    2,156 goal | 2706 cost |   2,260 actions | TOTAL\n",
      "\n",
      "breadth_first_search:\n",
      "      596 nodes |      597 goal |    4 cost |      73 actions | PourProblem((1, 1, 1), 13)\n",
      "      596 nodes |      597 goal |   15 cost |      73 actions | GreenPourProblem((1, 1, 1), 13)\n",
      "    2,618 nodes |    2,619 goal |    9 cost |     302 actions | PourProblem((0, 0, 0), 21)\n",
      "    2,618 nodes |    2,619 goal |   32 cost |     302 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "      120 nodes |      121 goal |   14 cost |      42 actions | PourProblem((0, 0), 8)\n",
      "      120 nodes |      121 goal |   36 cost |      42 actions | GreenPourProblem((0, 0), 8)\n",
      "    2,618 nodes |    2,619 goal |    9 cost |     302 actions | PourProblem((0, 0, 0), 21)\n",
      "    2,618 nodes |    2,619 goal |   32 cost |     302 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')\n",
      "       18 nodes |       19 goal |  450 cost |      10 actions | RouteProblem('A', 'B')\n",
      "       42 nodes |       43 goal | 1085 cost |      27 actions | RouteProblem('N', 'L')\n",
      "       36 nodes |       37 goal |  837 cost |      22 actions | RouteProblem('E', 'T')\n",
      "       30 nodes |       31 goal |  445 cost |      16 actions | RouteProblem('O', 'M')\n",
      "       81 nodes |       82 goal |    5 cost |      35 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "   12,111 nodes |   12,125 goal | 2973 cost |   1,548 actions | TOTAL\n",
      "\n",
      "breadth_first_bfs:\n",
      "      948 nodes |      109 goal |    4 cost |     112 actions | PourProblem((1, 1, 1), 13)\n",
      "    1,062 nodes |      124 goal |   15 cost |     127 actions | GreenPourProblem((1, 1, 1), 13)\n",
      "    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)\n",
      "    3,757 nodes |      420 goal |   24 cost |     428 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "      124 nodes |       30 goal |   14 cost |      43 actions | PourProblem((0, 0), 8)\n",
      "      124 nodes |       30 goal |   36 cost |      43 actions | GreenPourProblem((0, 0), 8)\n",
      "    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)\n",
      "    3,757 nodes |      420 goal |   24 cost |     428 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')\n",
      "       28 nodes |       12 goal |  450 cost |      14 actions | RouteProblem('A', 'B')\n",
      "       55 nodes |       24 goal |  910 cost |      32 actions | RouteProblem('N', 'L')\n",
      "       51 nodes |       22 goal |  837 cost |      28 actions | RouteProblem('E', 'T')\n",
      "       40 nodes |       16 goal |  445 cost |      20 actions | RouteProblem('O', 'M')\n",
      "      124 nodes |       46 goal |    5 cost |      50 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "   17,068 nodes |    2,032 goal | 2782 cost |   2,119 actions | TOTAL\n",
      "\n",
      "iterative_deepening_search:\n",
      "    6,133 nodes |    6,118 goal |    4 cost |     822 actions | PourProblem((1, 1, 1), 13)\n",
      "    6,133 nodes |    6,118 goal |   15 cost |     822 actions | GreenPourProblem((1, 1, 1), 13)\n",
      "  288,706 nodes |  288,675 goal |    9 cost |  36,962 actions | PourProblem((0, 0, 0), 21)\n",
      "  288,706 nodes |  288,675 goal |   62 cost |  36,962 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "    3,840 nodes |    3,824 goal |   14 cost |     949 actions | PourProblem((0, 0), 8)\n",
      "    3,840 nodes |    3,824 goal |   36 cost |     949 actions | GreenPourProblem((0, 0), 8)\n",
      "  288,706 nodes |  288,675 goal |    9 cost |  36,962 actions | PourProblem((0, 0, 0), 21)\n",
      "  288,706 nodes |  288,675 goal |   62 cost |  36,962 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')\n",
      "       27 nodes |       25 goal |  450 cost |      13 actions | RouteProblem('A', 'B')\n",
      "      167 nodes |      173 goal |  910 cost |      82 actions | RouteProblem('N', 'L')\n",
      "      117 nodes |      120 goal |  837 cost |      56 actions | RouteProblem('E', 'T')\n",
      "      108 nodes |      109 goal |  572 cost |      44 actions | RouteProblem('O', 'M')\n",
      "      116 nodes |      118 goal |    5 cost |      47 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "1,175,305 nodes |1,175,130 goal | 2985 cost | 151,632 actions | TOTAL\n",
      "\n",
      "depth_limited_search:\n",
      "    4,433 nodes |    4,374 goal |   10 cost |     627 actions | PourProblem((1, 1, 1), 13)\n",
      "    4,433 nodes |    4,374 goal |   30 cost |     627 actions | GreenPourProblem((1, 1, 1), 13)\n",
      "   37,149 nodes |   37,106 goal |   10 cost |   4,753 actions | PourProblem((0, 0, 0), 21)\n",
      "   37,149 nodes |   37,106 goal |   54 cost |   4,753 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "      452 nodes |      453 goal |  inf cost |     110 actions | PourProblem((0, 0), 8)\n",
      "      452 nodes |      453 goal |  inf cost |     110 actions | GreenPourProblem((0, 0), 8)\n",
      "   37,149 nodes |   37,106 goal |   10 cost |   4,753 actions | PourProblem((0, 0, 0), 21)\n",
      "   37,149 nodes |   37,106 goal |   54 cost |   4,753 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')\n",
      "       17 nodes |        8 goal |  733 cost |      14 actions | RouteProblem('A', 'B')\n",
      "       40 nodes |       38 goal |  910 cost |      26 actions | RouteProblem('N', 'L')\n",
      "       29 nodes |       23 goal |  992 cost |      20 actions | RouteProblem('E', 'T')\n",
      "       35 nodes |       29 goal |  895 cost |      22 actions | RouteProblem('O', 'M')\n",
      "      351 nodes |      349 goal |    5 cost |     138 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "  158,838 nodes |  158,526 goal |  inf cost |  20,706 actions | TOTAL\n",
      "\n",
      "greedy_bfs:\n",
      "      948 nodes |      109 goal |    4 cost |     112 actions | PourProblem((1, 1, 1), 13)\n",
      "    1,696 nodes |      190 goal |   10 cost |     204 actions | GreenPourProblem((1, 1, 1), 13)\n",
      "    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)\n",
      "    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "      124 nodes |       30 goal |   14 cost |      43 actions | PourProblem((0, 0), 8)\n",
      "      124 nodes |       30 goal |   35 cost |      45 actions | GreenPourProblem((0, 0), 8)\n"
     ]
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)\n",
      "    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')\n",
      "        9 nodes |        4 goal |  450 cost |       6 actions | RouteProblem('A', 'B')\n",
      "       29 nodes |       12 goal |  910 cost |      20 actions | RouteProblem('N', 'L')\n",
      "       19 nodes |        8 goal |  837 cost |      14 actions | RouteProblem('E', 'T')\n",
      "       14 nodes |        6 goal |  572 cost |      10 actions | RouteProblem('O', 'M')\n",
      "       15 nodes |        6 goal |    5 cost |      10 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "   18,120 nodes |    2,082 goal | 2897 cost |   2,184 actions | TOTAL\n",
      "\n",
      "weighted_astar_search:\n",
      "      948 nodes |      109 goal |    4 cost |     112 actions | PourProblem((1, 1, 1), 13)\n",
      "    1,696 nodes |      190 goal |   10 cost |     204 actions | GreenPourProblem((1, 1, 1), 13)\n",
      "    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)\n",
      "    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "      124 nodes |       30 goal |   14 cost |      43 actions | PourProblem((0, 0), 8)\n",
      "      124 nodes |       30 goal |   35 cost |      45 actions | GreenPourProblem((0, 0), 8)\n",
      "    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)\n",
      "    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')\n",
      "        9 nodes |        4 goal |  450 cost |       6 actions | RouteProblem('A', 'B')\n",
      "       32 nodes |       14 goal |  910 cost |      22 actions | RouteProblem('N', 'L')\n",
      "       29 nodes |       12 goal |  805 cost |      19 actions | RouteProblem('E', 'T')\n",
      "       18 nodes |        8 goal |  445 cost |      12 actions | RouteProblem('O', 'M')\n",
      "       15 nodes |        6 goal |    5 cost |      10 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "   18,137 nodes |    2,090 goal | 2738 cost |   2,193 actions | TOTAL\n",
      "\n",
      "extra_weighted_astar_search:\n",
      "      948 nodes |      109 goal |    4 cost |     112 actions | PourProblem((1, 1, 1), 13)\n",
      "    1,696 nodes |      190 goal |   10 cost |     204 actions | GreenPourProblem((1, 1, 1), 13)\n",
      "    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)\n",
      "    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "      124 nodes |       30 goal |   14 cost |      43 actions | PourProblem((0, 0), 8)\n",
      "      124 nodes |       30 goal |   35 cost |      45 actions | GreenPourProblem((0, 0), 8)\n",
      "    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)\n",
      "    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)\n",
      "        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')\n",
      "        9 nodes |        4 goal |  450 cost |       6 actions | RouteProblem('A', 'B')\n",
      "       29 nodes |       12 goal |  910 cost |      20 actions | RouteProblem('N', 'L')\n",
      "       23 nodes |        9 goal |  805 cost |      16 actions | RouteProblem('E', 'T')\n",
      "       18 nodes |        8 goal |  445 cost |      12 actions | RouteProblem('O', 'M')\n",
      "       15 nodes |        6 goal |    5 cost |      10 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),\n",
      "   18,128 nodes |    2,085 goal | 2738 cost |   2,188 actions | TOTAL\n",
      "\n"
     ]
    }
   ],
   "source": [
    "report((astar_search, uniform_cost_search,  breadth_first_search, breadth_first_bfs, \n",
    "        iterative_deepening_search, depth_limited_search, greedy_bfs, \n",
    "        weighted_astar_search, extra_weighted_astar_search), \n",
    "       (p1, g1, p2, g2, p3, g3, p4, g4, r0, r1, r2, r3, r4, e1))"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "This confirms some of the things we already knew: A* and uniform-cost search are optimal, but the others are not. A* explores fewer nodes than uniform-cost. "
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Visualizing Reached States\n",
    "\n",
    "I would like to draw a picture of the state space, marking the states that have been reached by the search.\n",
    "Unfortunately, the *reached* variable is inaccessible inside `best_first_search`, so I will define a new version of `best_first_search` that is identical except that it declares *reached* to be `global`. I can then define `plot_grid_problem` to plot the obstacles of a `GridProblem`, along with the initial and goal states, the solution path, and the states reached during a search."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 45,
   "metadata": {},
   "outputs": [],
   "source": [
    "def best_first_search(problem, f):\n",
    "    \"Search nodes with minimum f(node) value first.\"\n",
    "    global reached # <<<<<<<<<<< Only change here\n",
    "    node = Node(problem.initial)\n",
    "    frontier = PriorityQueue([node], key=f)\n",
    "    reached = {problem.initial: node}\n",
    "    while frontier:\n",
    "        node = frontier.pop()\n",
    "        if problem.is_goal(node.state):\n",
    "            return node\n",
    "        for child in expand(problem, node):\n",
    "            s = child.state\n",
    "            if s not in reached or child.path_cost < reached[s].path_cost:\n",
    "                reached[s] = child\n",
    "                frontier.add(child)\n",
    "    return failure\n",
    "\n",
    "\n",
    "def plot_grid_problem(grid, solution, reached=(), title='Search', show=True):\n",
    "    \"Use matplotlib to plot the grid, obstacles, solution, and reached.\"\n",
    "    reached = list(reached)\n",
    "    plt.figure(figsize=(16, 10))\n",
    "    plt.axis('off'); plt.axis('equal')\n",
    "    plt.scatter(*transpose(grid.obstacles), marker='s', color='darkgrey')\n",
    "    plt.scatter(*transpose(reached), 1**2, marker='.', c='blue')\n",
    "    plt.scatter(*transpose(path_states(solution)), marker='s', c='blue')\n",
    "    plt.scatter(*transpose([grid.initial]), 9**2, marker='D', c='green')\n",
    "    plt.scatter(*transpose([grid.goal]), 9**2, marker='8', c='red')\n",
    "    if show: plt.show()\n",
    "    print('{} {} search: {:.1f} path cost, {:,d} states reached'\n",
    "          .format(' ' * 10, title, solution.path_cost, len(reached)))\n",
    "    \n",
    "def plots(grid, weights=(1.4, 2)): \n",
    "    \"\"\"Plot the results of 4 heuristic search algorithms for this grid.\"\"\"\n",
    "    solution = astar_search(grid)\n",
    "    plot_grid_problem(grid, solution, reached, 'A* search')\n",
    "    for weight in weights:\n",
    "        solution = weighted_astar_search(grid, weight=weight)\n",
    "        plot_grid_problem(grid, solution, reached, '(b) Weighted ({}) A* search'.format(weight))\n",
    "    solution = greedy_bfs(grid)\n",
    "    plot_grid_problem(grid, solution, reached, 'Greedy best-first search')\n",
    "    \n",
    "def transpose(matrix): return list(zip(*matrix))"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 46,
   "metadata": {
    "scrolled": false
   },
   "outputs": [
    {
     "data": {
      "image/png": "iVBORw0KGgoAAAANSUhEUgAAA6oAAAJCCAYAAADJHDpFAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEgAACxIB0t1+/AAAADl0RVh0U29mdHdhcmUAbWF0cGxvdGxpYiB2ZXJzaW9uIDIuMi4zLCBodHRwOi8vbWF0cGxvdGxpYi5vcmcvIxREBQAAIABJREFUeJzt3b/PJFt6H/bTw11xTGsvocR2RFiZAgrv3dAADRJWaDhYLNATEPQGBmUl+hMM7ipQ4sxKSBAObqBgXoNYCIQyg7DBBQw48V7QViZIkeFQvCMTl7zwtoN55+47Pd39VnVVnfM9pz4foDC7z+3ues6Pqn5PV/XTh9PpVAAAACDFq9YJAAAAwHMWqgAAAESxUAUAACCKhSoAAABRLFQBAACIYqEKAABAFAtVAAAAolioAgAAEMVCFQAAgCgWqgAAAESxUAUAACCKhSoAAABRLFQBAACIYqEKAABAFAtVAAAAolioAgAAEMVCFQAAgCgWqgAAAESxUAUAACCKhSoAAABRLFQBAACIYqEKAABAFAtVAAAAolioAgAAEMVCFQAAgCgWqgAAAESxUAUAACCKhSoAAABRLFQBAACIYqEKAABAFAtVAAAAolioAgAAEMVCFQAAgCgWqgAAAESxUAUAACCKhSoAAABRLFQBAACIYqEKAABAFAtVAAAAolioAgAAEMVCFQAAgCgWqgAAAESxUAUAACCKhSoAAABRLFQBAACIYqEKAABAFAtVAAAAolioAgAAEMVCFQAAgCgWqgAAAESxUAUAACCKhSoAAABRLFQBAACIYqEKAABAFAtVAAAAolioAgAAEMVCFQAAgCgWqkAzh0M5HA7l88OhHBJjAAC0YaEKtPRQSvmTp38TYwAANHA4nU6tcwB26unq5UMp5cvTqZzSYgAAtGGhCgAAQBS3/gIAABDFQhVYJKn4UcuiS2n5AAD0zEIVWCqp+FHLoktp+QAAdMt3VIFFkooftSy6lJYPAEDPLFQBAACI4tZfAAAAoliows71WjAoKZaWTw/9AABwi4Uq0GvBoKRYWj499AMAwFW+owo712vBoKRYWj499AMAwC0WqgAAAERx6y8AAABRLFRhUAoG1Yul5aMf5ucNAGSxUIVxKRhUL5aWj36YnzcAEMR3VGFQLQvl7C2Wlo9+mJ83AJDFQhUAAIAobv0FAAAgioUqBEsrOJOUT1IsLR/9kBeb+1gA2DsLVciWVnAmKZ+kWFo++iEvNvexALBrvqMKwQ5hBWeS8kmKpeWjH/Jicx8LAHtnoQoAAEAUt/4CAAAQxUIVGkgq8qJQjr7RD/oGAOKcTiebzVZ5K+X0eSmnf13K6fNeYmn5JMXS8tEPebG0fK7laLPZbDZbytY8AZttj1spp8PTH4qHXmJp+STF0vLRD3mxtHyu5Wiz2Ww2W8qmmBIAAABRfEcVAACAKBaqcKekIiiKweibhFhaPkmxtHzm5A0ATbS+99hm63UrQUVQasTS8kmKpeWjH/JiafnMydtms9lsthZb8wRstl63ElQEpUYsLZ+kWFo++iEvlpbPnLxtNpvNZmuxKaYEwCYeHx+/KqV878J/enc8Hj+rnQ8A0A/fUQVgK5cWqbfiAAClFAtV+ERSIZOkWFo+SbG0fNL64ZKkvM2R+W0BgK1ZqMKnHkopf/L0r9jHkvJJiqXlk9YPlyTlbY7MbwsAbMp3VOHM05WDh1LKl6dTOYmVb08SSfkkxdLySemHt28ff1GuePPm+Colb3NkflsAYGsWqsC3FL9hTY+Pj1ffYI7Ho1tJJ3BM8pz5AOyJW3+B5xS/gSyOSZ4zH4DdsFBlt0YveLJFsZSkHJNiafmk9cMlSXn3MEeS+hAAarBQZc9GL3iyRbGUpByTYmn5pPXDJUl59zBHLkk7PwDAanxHld06XCkScim+l9it4jfH4/GQkGNiLC2flH5QTGn5HEnsQ9rxvW9gTyxUgW/t8Y8gxUm20+N8SpsPPfYh2zEfgD1x6y+wd4qT8Jz5AAABLFTZhVoFT0aJLe3HHmNL2pvWlpZ9uHbf9jgftpgj6X0IAGuzUGUvahU8GSV2TVKONdps3syL3YqfS8q7Rs5p+dQ6ZwDAXXxHlV04zCgSMvWxI8b2WExpjWI1KW1pHduib3ucD2vOkV76kDp8RxXYEwtV4Ft7/CNoj22upce+Tcs5LR/aMh+APXHrLwAAAFEsVAEAAIhiocou1KrMOUpsaT/2GFvS3rS2tOzDtfu2x/mwxRwZpQ8BYCoLVfaiVmXOUWLXJOVYo83mzbzYrfi5pLxr5JyWT8vzCAC8SDElduHpU/6Honrr3RVGVf01b+b2Qy8Va2vknJZPrfnAuhRTAvbEQhX41h7/CNpjm2vpsW/Tck7Lh7ZuzYcL3h2Px882SwZgY279BQAYz/daJwCwhIUqw2lZ8GSU2BZ9mx5b0t60trTsw7X7tsf5sMUc6bEPp7YDAC6xUGVELQuejBK7JinHGm02b+bFbsXPJeVdI+e0fJL6FQA+4TuqDOfp0/uHUrHgySgxxZQ+ppiSYkpr5ZyWT8s5wv1mfkfV95iBrlmoAt/aY+GWPba5lh77Ni3ntHxoy0K1nsfHx6/K5e/5KlIFlbj1FwAAPnatGJUiVVCJhSpd26LQR1LhkbSCJ0k51mizebNOPyzp2x7nwxZzZKqkPlzSDgCwUKV3tYrB7C12TVKONdps3syL3YqfS8q7Rs5b5LN2ji3PLQDwEd9RpWtPn9Q/lI2KwbQuPFI7ppjSxxRTUkxprZy3yOfS9w8T+lAxpe34jmo9vh8O7VmoAt/a4xvz0jZPLbhx43Gj+KTASI/zKS3ntHxoy0K1HscetOfWX4BlphbcGHmRWsr47QMAKrJQpRu1Cn0kFR5JK3iSlGONNm/RX6Nb0uZR5sMW55a1JfUrAFxioUpPWhaD2VvsmqQca7R5i/4a3ZI2jzIftji3rC2pXwHgExaq9OTLUsoPn/7dKlZrP+mxa5JyrNHmLfprdEvaPMp82OLcsrakfgWATyimBDs1t7hPo0IyaQWI7i4YNLcISo/O50iPxUjSck7KJ/B4nOOTY7dHoxRTmlqELiCfdEPMa7jGFVXYrx7elNNyXJLPu9WygDbSjsc5es59RFOL0NXS6/zoNW+Y5DutE4BLDg1/46/VvmvH3r7NH5d7ctzatXnz8mPff+p9Xz9c/y3NNGuPX/qc2/rcUvMYSMoFAFxRJVXLQh9JBV3Sipv0kOPW5uQ3cj9cs3be6XOu1rmlhqRcANg5C1VStSz0kVTQJa24SQ85bq1l8akerJ13+pzrtZjSJUm5ALBzbv0l0tNtZz+vHZvy2A9FF57fBvf4+P7foNi7p1tNb7SjzFZ7XO7JcWvX5s3Ux47SD9esnXf6nFvz3LJGPksk5QIArqjCfD0UL+ghxynSChC1yietHy7pIUeW6XmMe86d7fU6P3rNGyZxRZXmEgoLzSl40ktBkRGKKV0qQHSrsNDaP8UwZ94sef49/dD6WJly/NyaY0l51ygA1TKftfgZDEZ1aW7X+GmopJ+fgkSuqJIgrbDQKAVFRiqm1GtxmaT+ann8XJKU99rza+m5pcfzDQCsykKVBGmFhUYpKDJSMaVei8sk9VfL4+eSpLxrFIBqmQ8AdMetvzTXqnDS/cWUJjQqwBbtSBirpOIyaz1/QQGvF4tm1Yx9mvf5f22fY435tWahtltu3TZ4h3du7V3Xh/FsnMOQc+RG38bkCCzniirM10PxgrVz7KHNI7v2x+4oRbN4r+V4mkvrG61Pk9rjnAg74IoqVSUUS1laTKmXwjZLirS8eXN8dV/f9FHsZqqUYkq9FCXqNe8aOS/ddw0t5w0AnHNFldqSiqVsUfCkx9glPfRNDUtzaTVWacdPet41cl667xqS+hqAnbNQpbakYilbFDzpMXZJD31TQ1oxpRr7UExpm5yX7ruGpL4GYOfc+ktVCcVSbsXS8mlVNGZaoZw2BX72WUxp+32sEes17xo5L913DS3nDVwztyjVygWkgIZcUQXupZgFrKtl0TIF09Y3Wp+2ao/3FNgpV1TZTEJhlG2KKY0Ru6dwS0KhHMWUttmHYkrb5jztsWMUalurb3pX62dSbl1BPB6Ph62eC7A1V1TZUlJhlC0KnowSm2Pq89PyvtfSXGq0OW0u9Zh3jZxbtiU9disOwE5ZqLKlpMIoiildj82RVCinBsWU5ufXY95pxZT2FrsVB2CnDqfTEHfYADfMLUbRqxa3qi287a7luLzb+tbEjvvmIrdCru/GOG8+P0fR462/c/abWBxprb6p1f+jv9cwLldUYR+i/uDnWy3Hpca+rxVfmVKUJW3OjlYYJ4WibMstOc7Yh9HfaxiUYkpsJqlYx96LKdUsQMQvpY/L9sfP/cWBWvfNmzfHV8W5pdp5N11ym12t+liNq51AHa6osqWkYh0KntBC+rj0cPy00kPfjBLrwR7bDNCUhSpbSirWoeAJLaSPSw/HTys99M0osR7ssc0ATbn1l8083eL0855iafmsFXt8PG8lNaSPS/Lx02PffChY8vy25ad2vDsej58lnAsSY/eqWSDm0pg+3dpetc2XbNUPE299VSgH2IwrqrAPimpkajku6XOix75RGKguBWLe0w+8pMfzKbiiyjqSCnMoeHIp9mlRm7dvH39xbTwvFZKZ8/xWP2uQ5p5xuVxYaN5YjXH83F+IKbVoWUKOibFepRxTrQuPkc9Vb3rliiprSSrMoeDJvNglc/qG61qNleOnbeyapByTYr1KO6YAhmKhylqSCnMoeDIvdsmcvuG6VmPl+GkbuyYpx6RYr9KOKYChHE6nru+8Ae506xbaKbfuLn3+hde7VhDko2Ida+93qRr5pLV5bTWL4rQywjhtYcncbv01gJQx7bEf5oz73Pb1dN6duo+Ac6SiWTThiirs17UCB60KHyhEs1/GmHsoEPOefhhf63Nk6/2zU4opMVtSEY7sYjDpsXnFas7jey3gMacYTI0iPRlzadnxs5e5lDRWSbH7+7C/glvbHFP390OrongAU7iiyj2SinC0LFyxt9it+J7M6YMtxmDrfbQ8fkaXNFZJsTmS8u7hmHLsAd2yUOUeSUU4FIOpF7sV35OWxXNq7KPl8TO6pLFKis2RlHcPx5RjD+iWW3+Z7en2oZ+PGEvLJyl2Hn98PP+v+3Ctby55flvdU3+9e7pNb9YY3Orr5DkyNbaXuZQ0VkmxORLy/lDY5vkt6x/m8NqxGY9d/dwC0JorqgDLzCkmoiDFZQqy0JPE4zgxp1vSivmla90vrffPTrmiyk1JRSVyClfsM3Ye30MBnCl986Fk/9QCJYoptS0Gs2U/3Mql1hj0GOutv1LPfT21xU+dzKO/2CtXVHlJUlGJkQpX9Bi7FR/VFn2zdAzWfL2Rjp+pWuaSNFZJsWuScuzh3DdSWwAsVHlRUlGJkQpX9Bi7FR/VFn2zdsGTHuZIUjGYlrkkjVVS7JqkHHs4943UFgC3/nJbQuGKmrE1X/NGwY27il60jn3avvP/Op4t+mbtYkPJc6RGbO48bJlL0lglxa6pP5emnbNTz301jh+AmlxRhe1cK27RW9EL2lN4BLY39ZydeNwl5gSwiCuqfCuhSEXr2Jqv2UsBHMWU3qvVN7WLDfV6/PR4nL10TCSNVVIspb+mz6V6x2NOm+uOPUAprqjysaQiFS2LY2zxmueS2ry0b0ZRq2+SxrSH46fH4ywtn/TYNUn5jH5MXdJy7AHK4XTyoRbvJX3CPsIVoVs/VfHmzfFVSpvvv2o472dBXvL4+Hj1ZPT89aY+bq5afdPj2Kdc/Uk/zl46JpLGKiV263hOGr9Wx+3obZ7i1hy5ZMn7wNT99rQP6JmFKmxk9DeguX88hHu35u/UJY39hwIxNfd5p7vGIKyvV8+lo/Gb4pMxHn380vXQZgvVm89veX5Y9X0TLnHrL8A4C4FLemlbL3nWNlK/jNSWUSjU1reWx5Tjmc1ZqO7U4VAOh0P5/OlWHLEN++aSpDYv7ZtR1OqbluOXbpTjrFb7elSrv0aaS1vu53g8fnY8Hg9v3hxfvXlz/P6bN8dXx+PxcDweP0vqf2CfLFT3q1VhiPTYVq95LqnNS/tmFLX6puX4pRvlONsin1HU6q+R5lLS+4BzFVCNhep+fVlK+eHTv2If2+I1zyW1eWnfjKJW37Qcv3SjHGdb5DOKWv010lxKeh9wrgKqsVDdqdOpnE6n8vPnlffEtnvNc0ltXto3o6jVNy3HL90ox1mt9vWoVn+NNJda7Tup/4F9+k7rBAACjFw45F3po+jFyGOwRC/jN4UxZnMXKumOXJ225fnB8czmLFSB1SX8jmoPP7tQw8B/oO2C8YPFRvmg5xPOD4zOrb871aqaX3psq9c8l9TmpX2zdvumvt7aj+uhb9Jjrfed0tdp+aTH0vorLZeksUoaE2B8Fqr7lVThLym21WueS2rz0r65pEZ/rf24HvomPdZ63+eScmmZT3rsmqR89nhMJcWAHTqcTr6/vkdPn1Q+lFK+/FDEQGzdvnn79vEX1/r/zZvjq5Q239s3a7dv6uut/bge+qaXWIt9J/X1rVyOx+MhaaxSYrdu0U8av1bHbdJYtYrdmiNTbfl1lCV8RQVus1CFjYz+BrR2+0b6juroY3/J4+PjV2Xg74KVCQVZ9jjuSyX12RoLojBDFBGyUIX9cusv0JtrlQZVIGxr5EVqKeO3j/GYs/m8n8ENFqqDu1aUIKlIQlJsq9c8l9TmpX2zdvteer3j8fjZ8Xg8vHlzfPXmzfH7b94cXx2Px8PxePysVf/X6pv02OiW9kPSWCXF0vprJEnjbEw+9eH97MLW/ZVwWIOF6vgUZ5gX2+o1zyW1eWnfXJLUX2u/Xsu+SY+Nbmk/JI1VUuyatHx6lDTOxgSYxXdUB/f0ieRDUZyheuGKxMIca/ZNq2JKif3fct8psQG/3/eJl8ZOMaV1501SMaVejXC+Gfk7qsBtFqqwkaQ3uRuFbu4uttGqmFKr1+tl31PsoPDRJl4au/RxT5TUZyN+2DLCvLNQhf1y6y/sw7VFyZLFytpFIBSVqMcidT7zkN6Ys0DXvtM6AdbT4vbW0WJrvubbt8vHKimXT+Pvr8Sul/e6r1ez/1vue+2+GUn9W0dv55Mw9omxlP66NX49XEFLGtNacwQYmyuqY3ko7QoGjRLb6jXPtWzfvbm0zDu9/1vue+2+GUlavyaNfVLsmrR80iWNqTEBFvMd1YG4opp2RTWnoM4auaSNVVL/t9z32n0zkqTjTDGly7Feiim5opo5R6byHVXok4UqzDS1MNHMN9e7ixpNscc3XMWUrhuxaMwlScV4EsY9UVKf1chlwEJmm753laKYEuyZW39hvi0KE430hwv59lBkpUUbFQTjJaOd62u0x/EDO6WY0kDc+lvn1t+phXLmFqxpVSRk1HmjmNKt2NqFsPqcIzX7NSfHvNg1SecMrtt6nD5csfWVBtgfV1TH8lDGLopTIzb3seemPm7qc7do3737rZVjUpuX9k2NfSfF0vJJiqXlkxS7Ji0fLks7foBB+I7qQFz1qHVFdVqhnLmf7m5ZOEQxpW37uuW+k2Jp+STF0vJJie2tmNKI3w+vMU5THrv2+PmOKrRnoQozTX3zmvsHyZZvfFu84U4tKlVD4wIln7S3xz9wAoq8VJ83SwT0Vw1NC+UMWkxpuD+6Us5pa49f2NyMeb+Fmtz6C9xri6JS92q5YBhlsdK6Ha33P1dv+d6jZaGcUQvojNau0dqTKun9FqpRTGkgbkGrdXvRtDEYvZhSUsGghCIoqX3Tax8m9U1qf9Wwdb9OLZQzyphuefUroQ9T35vv6cO553Fgfa6ojuWhKOqxNDb3seemPm7qc7do37373eI1a7SvlvS+6bUP02OjSzvvGtPrkvow7b15qhrv9cBEFqpj+bKU8sOnf2/F5jx2b7G5jz039XFTn7tF++7d7xavWaN9taT3Ta99mB4bXdp515hel9SHae/NU9V4rwcmUkwJZlJMabvXvLCPLgrWnLc3qQjHVAlFXvY2b3qQOl+3sONz2hAFeQYvpjQ5l9A5dq8h5ib3c0UVSNbDm+0oxURat2PN/fcwb3rQek6MKHFuJuaUoNdCXyON50ht4Q6KKQ1EMaX2BRsUU1q3La0L1tz7G7M9FlM6nZYXtUlpS+t5s4Wpv9Hc4+/0puQz4ryZKqH/a7031zwnLm0z7J0rqmPZoijB3mJzH3tuSYGFWu27d79bvOaSvGvooW+SYon5jGLk+ZWYz94k9X+t9+b0GOye76gOpLdPrxNjUx479WrGrce99Nz1rxQsvwKzxWsuybuG5L5JjKXk03rebMEV1bbzZsXvqEb+0ZU+b6Y8dsTj4oOZ31GNnGP32tP35PmUhSrMpJjSdq85Zx81hPfNtYIZuy8+0XrebGHquWXvf9QNVkimmhHmTY/Hhfn6stSxow63/gLJWhat6LVghj968sdurtHasyXzfz7zqx3z9TZzc+cUU+rUCLdZJcamPFYxpfVec8tiFjVvA2vRN4kFm1ruO33erNm+xLFPmTc9F0S6NL9KyRqr5DnS43HR03x1ZZMWXFHt10MZp3BFUmzuY89NfdzU527Rvnv3u8Vrpre5h76psY89nlsuSeubtXMcad70aPRjqtYcuSSpLaPMV9ic76h2KuXT69FiUx6rmNJ6r7ntJ9Utr6i2LTTVqv9r7afHedNDjsnn3TX6Jp0rqnXem1u3pdf56ooqLViowkzpxZTmFmdILhi0RMv8WheaSuj/XvXQrz3k2ErPhbT2PnbXTC0ct+S4aFWcrqf5an7Sglt/YTyKMwB71WvxlV7zrqFG4bhWxel6Gfde8mQwiil1KuU2q9FiUx6bXkxpq/3O2U/CmNbMr8W+E/u/5b7T+7WHHMeYN/cX0kqMpeXTsh8uWeu4aHdMTZuvNX7jFxK5otqvh5JVuGKU2NzHnpv6uKnPXdqWNfc7Zz9pY7p1fq33vfU+9nhuuSStb9bO0bzJi6Xlk3Q8znnsKMcU7IrvqHbKJ7T5BRtaFVPaar9z9pNQuEIxpczjJz2mmJJ5kxRLy6dF7Nb3OKe+5750XKQfU66osleuqHbqdCqn06n8/Pmb2dTY0uePHJv72HNTHzf1uUvbsuZ+5+wnbUy3zq/1vrfexxbHT3ps7X7tIUfzJi+Wlk/Lfrhk7eNiyXNb9gOMykIVAACAKBaqnTocyuFwKJ8/3RoyK7b0+SPH5j723NTHTX3u0rasud85+0kb063za73vrfexxfGTHlu7X3vI0bzJi6Xl07IfLln7uFjy3Jb9AKOyUO3X0i/j1/jSf4+xuY89N/VxU5+7tC1r7nfOftLGdOv8Wu97633s8dxySVrfrJ2jeZMXS8sn6Xic89hRjinYFcWUOvX0CdtDUZxh1diUxyqmNK8fWo2pYkqZx096TDEl8yYplpZPi5hiSoopsV8WqhM8Pj5+VS7/6PO74/H9b2CxH7feNJ+/Ydx63EvPXaLWfqf2Qyst86ux7/T+n+PGOXYUq75XjDT21NPr3zJrvOe+dFzM2Mfo56pSwucDl/V6fL/Erb/TXDspjX6yYpl3rROATox+Lh29ffRh9L9lrr3nrvlePEpf3bKHNo5oyOPbQrVTS7+M36oQQHps7mPPPX/c8Xj87Hg8Ht68Ob568+b4/afbhyY9d622TLG0b2q0Ze1+qDVvau17631scfwsmbO9GnnsW86bkWNbvea5pDbPOTc8f+yl99zj8Xg4Ho+frd03QB0Wqv1a+mX8Gl/67zE297Hnajx3yT6W5tyqLWv3Q615U2vfW++j1rlldCOPvfekbWJbvea5pDbPOTe06hugAgvVfn1ZSvnh079zY0ufP3Js7mPP1Xjukn0szblVW9buh1rzpta+t95HrXPL6EYee+9J28S2es1zSW2ec25o1TdABYopTaBwBc/VKNiwhGJK7ymm1I+5c7ZHa45Jq7EPKCRzV1GQUYuMzNXrOSPpfLqHc1Up2fOBy3o9vl/iiirUVaPYA+0Z53lG75dR2te6KMe9+x+yyAhNjHIs37KHNtKJ77ROgJc9fYH/oRS/y7Z1bMpj375dMlbvP73fsi238rsv52u/Fbr8NVv1w/bzpu04Jx8/rY6L1r9Rum6O1zLMOrdsoaf+Snu/7r0ftsx7et9MO1et/bunc66WjXpljX1yRbUPWxQLWPs1R4nNfey5tLZMsbRvlrxmq34Y6Zi6pIfjJz12SVrfrJ3j2ueWLfTYX+bNNjnX2k+vxwp0z0K1Dz0UZxglNvex59LaMsXSvlnymq36YaRj6pIejp/02CVpfbN2jmufW7bQY3+ZN9vkXGs/vR4r0D3FlCZwGwXPpc8HxZTe20vRi0sS+r9X6fO6lKbFlJofU1vfNjmyhPFbW2pxupavZ77v06jj7ooq7NvIRRNGbhvbUQjrutZ90Hr/AFSkmFIHkoszjBab8tj0ghS38luzGEx6P1wqenGrwMVIko+f/Ng2hZ3WfM2tCqaN0Dc9nrNT500PUufIiH0NLbii2octigXUKH7QY2zuY8+ltWXN/Grtp1XfjKSH42dvsa1ec4qkfmg5by5J6oe0edOD9DkCLOA7qhO0vu87+RPa0WJTHrvVz1es98lwnZ/XSO+HuX0zklb9X2s/PcbWfM25P32R1A9trqj2d66qPW96tdb4rT1H/DwNtY067haqE4w6+NxnZkGKd8fj+9vlaqk1X3s8LkYsJrKy6vO1lsfHx69KKd9rncfWUo+9lno8V23B+a8rH52L1xq75/N9B+fEYd/PLhn1POfWX9jWyG8CPVKM5baR5+vIbQPGUuN8Nfo5cfT27YJiSh1IvpVotNiUx7YrZNK2cEit/WwbyyoGk3gr3qjnlj0XN0no/7a3/uqbl/oh+RZoV4Jhv1xR7cNDyS/OMEps7mOnaNmWNXOptZ8eY2s8P8Xo55Y9Sur/lvPmkqR+qNU3lyS12XELlFJ8R3WS1vd9J39CO1psymPnXgWr/Um1YkqZ86aXK6przpHW45Le11tQTKneObG3vum1H/Z6RfXs+6Sr9MEWr5ms5+9mztV6rbIVC9UJRh12sESyAAAgAElEQVR87jP35F57jiim1I/EPxS2HrsdFPBoyrH3qdHPVTeOqckFeZL7IfE8WYOF6nLJ83ptvR7fL3HrL8ynIA9rSZtLNfKxSIV1XTumHGv9qnEuTnv/Wdvo7dsFxZQ6kHwr0WixaY/9tCDPrVuq6t/ieC2Tdfum5wIlOcfU/cWdEm/jm5b3tazzpdwWvcZtzGMcP23PiSl9M7V9vffDJWtdKVr7alQPV7f29NMt9MsV1T48lPziDKPE1nj+uZZtWTOXWvvpMdZ63+d66Icepc2RJfZ4/FyS1A9bHFMj9QOwMxaqffiylPLDp3/XiG3xmqPE1nj+uZZtWTOXWvvpMdZ63+d66Icepc2RJfZ4/FyS1A9bHFMj9QOwMxaqHTidyul0Kj9/fgvMktgWrzlKbI3nn2vZljVz6aHNvc6bpHGu1Q89SpsjrdrS6/GT3g9bHFMj9QOwP76jCkBN70qfRV6aFOaYWyW5USXPd77vRgsX5vuoc3GV86bzA72xUAWgGn+wzNbDor6HHNmHIefitfNmJz8xM+SYUIdbfztwOJTD4VA+f6qEtzi2xWuOElvj+edatmXNXHpoc6/zJmmce+2H9Ngaz0/Ww7xZO++0eTO1fb32A7A/Fqp96LXCYo+xNZ5/LqlK4hZ9s/Z+eoy13ve5PfZDemyN5yfrYd6snXfavLlkpH4AduZwOvVw10BbrX8P6+lTxYdS+vjNup5j9z4/6Tctt8oluc2tYy32ndj/aeOSFNtinJOk/MZsL8fKmn0ztX299sPc21sTfve01t+Nndz6G/PbsSNrvVbZioXqBKMOPutJmiMJb5COi/vNLZ7TAYU0FujlD9EFNp8fS85VvR+Pz9vX6znbQvW+/SRJnl+j6PX4folbf4F7XauC2qQ66kC6/aP4itHaU9vox1P6/EjPbw7nbFowv7ibqr9hUm4l2mvs3ue/fdt2TGvk8mn8/VWQpPHrbd7MHb9eJY1Vf3Pk/uOsl9uGS8k9J/Z+PI5yzmYdPV9ZY59cUc3zULKKM+wttsbzz7Vsy5q5tGxLemyr1xxF0liNNEdGmkvp58ReJR0Do89hYGW+ozpBzfu+sz/ZHz927/OTilTUKqbUeqySYrXGr1fJhVpqxVrsu5e5dDweD6nnxF768JoRjj3fUb1vP1vvmyyjfkfVQnWCUQef9STNkaRcmK+X4hhzmHdt9DKXtp4fC4spddGH14xw7LVeqFZwd0ExC1U+GPVvP7f+AmQZrfDEaO3pSQ99n55jen57MPoYjFSwC1almFKYUW9B6yV27/P3WUwpb/x6mzeXY30XPEnKJynWZt99zKWt97PsnNi2D6e17/rtyUnjfG/sw9XGkW7JBqZxRTXPQxm7qEd6bI3nn2vZljVzadmW9FhaPvohL5aWT1Ks5n7OJfXD0r65JKktW/QDMDDfUZ1AMaX9xO59vmJK+46l5aMf8mJp+STFtt5P0vm59hXV9Pbd2w+32tzhd1Tv/lvSd1T5YNTvqFqoTjDq4HOfx8fHr8qM75SMUExpbptXdnehCUjQ+PhZYohjb/T38B20r9fjZzILVZYa9Tzg1l+Y4PCTw+Hwk8PvHH5yOJT8N8xrhSeWFKRo2eb0/oaX9DqHe8373BbnROoZZR5eYx7CFYophUm5lWivsUvxw08Oh3Iqf1hK+f1Syh+fTqdyOEz/cKp+W7Yp/tFS0hxxTOmHe/umR2PMmz6KSt1/62/b8dvj8bPkZ42m3o4NuKKa6KFkFWfYW+yj+NMV1D8sp1e/Vw7lUE6vfu+P/58/LjNvmU9q39K+aSWpHxxT12Np+STFemXetI3Nfey5pLbs8fi5ZIw2Hw5/pxwOf+/Z9ndap8R4fEd1AsWU9hP7KP47P/6y/M5P/rCU8rullP/ww3//1cOvlt/69d8qv/+f/P6kK6sjFLNoXWgivQ/T8tEPWbHWx88SNY69LV5zlNiUx45eTCnx+Em5otrsO6qHw2+WUv68lPIrz6L/XynlPy+n0/+5yj6YZdTvqFqoTjDq4HPdt1dS/+bX/mH5W3/16QP+5tfKP/iP/rNJi9UR5kjrPxRG6EP2q/Xxs8Tej70eCsmN/jdK4vGzZKH6/LmhhaJuz7vD4Tf/snz2F98rX310W+YvSinvymfl18tXf99itb5RzwNu/YUz3y5SS/ndi4vUUkr5W39VfvaXPyt33Abcq5bFHhSaoHe9zuFe816TQnLtpc3DKflMLeCVOMbXc3p/e++fny9SS3m/oPhe+aqUUv7cbcCsRTGlMCm3Eu029qFw0unV75VXv/gPbo3VX5/+uvzsL39WSik3r6xGte/O2IdPV1PySYul5aMfsmKOn37nza1CRbUsyTGhD7c4fta+3Xnu77K+nPe0Yz5hfs30H5dSfuXaVa5XpZRTKb/y4/Lj3/4nh/Ivlt7aDK6o5nkoWcUZ9hb77VLK77+0SP3gr09/Xf7s3/1Z+Vd/9a9uPSypfebNNrG0fPRDXiwtn6RYWj7XcmxlSY5JfbjFHLmkxjiPNL9W9Yvy6tVPyw/+h7KjNrMd31GdQDGlHcVmXFEtZVphpRGKWXxoS1I+SbG0fPRDXiwtn6RYWj5Tr7TVcDweD0tyHPX9J/+Kah/z65qrf9seDn+vlPK/lxu3B59Keffj8uP/+p+UP3BFtaJRv6NqoTrBqIPPZR99R/VZtd9zU6v/7mmOhBaGWNOk4iZr20G/ltKob9cUOk7d92tLrQv5THn/2OPfKGu3uUYfhp4fZvnuv//35b/8x/+4fOev/uriLZm/KKV8VX69/N3yb8q/K99+TfXd6VScgzY26nnArb9w5vQHp1Mp5R+VUv55+Ztfu/ygv/m1WT9RsyNdvwlP0Kp9o/drKWO0MbENiTn1RCE51tL9sfjN3/7b5c9+8pPyrnxWzi8Ff1ik/lb52fNFaikDtJt2FFMKs/fbrFrHfhk/PZTf+fE/Kt/7v/9h+fv/vHxU/fdvfq2Uv/jd8vu/+w8mLVKT2rf1vOmwMMRsLY6pPfRrKVnzfaRxSuibft+T2hbCmvLY0YspXWrL2m2u0Yep54e5vvqN3yj/23//35X/4g/+oBx+8cvl6v/79a+W3yo/K/9X+c1PnuPWX+7limqeh6JwRcvYL+P/y48fyp/+USl/8bvl2yurT4vU8qd/NOdKalL7as2bkbU8pkaXNN9HGqekvvGeNC8297HnktqyRT9csvaxO/r5YbavfuM3yr/8Z/+s/M//9J9+u/3d8m8uLlKfDNkPbM93VCdQTGk/sfN4KeUXpZxK+a/+21K+/z+W8n/8N6X86R+VUg7l7dvHSWM6ajGLngpDrOnSeJay9ZW68fu1lP6PldRxSu/XtHySYlMeq5jS8jbX6MPU88Na3rw53vrPF983Wc+o31G1UJ1g1MHnZYfDhxPqqZT/9H8t5d/+dinl/ZBPXajuaY60LjxSQ4vx3EO/ltL/sZI6Tr33K7ft8W+UTosp3X1++NGPflC+/vq7F/7LqXz4myTZ6dRBkp0b9Tzg1l+Y5FDKv/2dcscbwt6KYYze3lbtG71fSxmjjYltSMwJ9ujuY/HyIrWUHhapxTmIBRRTCpNyK9FeY+fxOWNXyji3Wd0/b7YvPJJ4m9v2+2lb0CWnH9Jj18cpJ8e8WFo+SbEpj1VMaXmb6/Th/efxUj4pspts0vswTOGKap6HklWcYW+xW/Epktoy+ry5RN+0jaXlkxRLyycplpZPUmzuY88ltWWLfrhk6X7WfL0t+iHdSG2hMd9RnUAxpf3EzuPlxqeYl76j6orq9rF9XlHtI5aWT1IsLZ+kWFo+SbEpj008J25/RbW/YkpLYsUVVV4w6ndULVQnGHXwednhcP2EemmhemcRh6/K5R/Efnc8vr9ViF8a/Xi8MR96NeQ8dtz2Y8BjarIRzomX9FhMaarDoXQ9X08KJzWRNIfX5NZfaO/aG1K3b1QsMtq4j9aeDxy3/TAm9GTGfI272KRwEquyUA1zOJTD4VA+f7pNYpNYrf30GLsVn2Lpvtd8vdHnTVJ/1Wpfr5LmTat5mJZ3UqzmfvYmaZy3mCNrtzmpDy95+/bxbPufPlzBfFVK+X4p5dXpVA4NY5859liThWqeqV9CXxKrtZ8eY7fiUyzd95qvN/q8uWSkvhlJ0rxpNQ/T8k6K1dzP3iSN8xZz5JKR3lemShorxx6r8R3VCRRT2k/sPF4qFFNKL+KQNm8S+6tW+3qVNI9bzcOUvBNjLcdqdKMce+fxkYsplZl/dxyPx0PSWF0bP7Y16ndULVQnGHXw+dhhZgGDS28YHVq18MsOipZsXijn1vmmVysXGYvnfSHLiMfUyrorAHZpTH/0ox+Ur7/+7qWHvzudys32tfo7b42/O5xvKGXctYpbf+GXJr9ZvH79zZZ51LT2QqDLhcUMNdo3WjGKe9sz+lyintGOqbX1eKx9MqZXFqmlZLdvj393wGTfaZ0AL+vtNqueY9cMcvX0ojXnzdu3tbOvb/tj6v2VjaTjos0t0PeMTgbn3bT3pOxjKuHW5IR+mDdHPh3TcuOW2SXnm41v873l21uOX5ojaWMFa3FFtQ8Ppc/CFT3G9miLeTMyx9T12Fav2RtzZF4sLZ89vv8k9cMW7z81nrv22M+ZI2ljBavwHdUJWt/33d+n133GDofrnwaOfEV1aqGIa/G0KwNbUyin1hXVfueSOeI9aU4sYa6nF12a8thy44pqeXZ1cu4YbNk3U3O+lV9aMSXaaL1W2YqF6gSjDj4fu7VQPff69Tfliy9+umU69KO7QiQ96LkAjvcF5kiY673N2cPMIkQXfFRgacnfeSvkctHp/e+UllIy5kgF3ksXGHWt4tZf+KXJBTduFG1gf5ILdfRMARz2ovVcb73/eyw976553t7iPaDHMVnKeymfUEypA26zqhP78OnqjNtyPpH6+20Jt5bVsOUtWj0Vs0i+PW96rN8COM673pPmxa7P9SnPn3t+T7/Nd0o/3Grf86/qvHlzvPq4j/vw+utNuH13DS/cmrzSXqAzrqj24aEoXFErdis+xdJ9r/l6S9rRq1pzpNW+02Np+bSaD/pmXiwtn6TY3MdOkdS+pf2wxJLjuUYua+8DuuM7qhO0vu/bp9dNP7W9+kn1pQJLrqi21eqKaloxi5Tjp3U+ra6oKqZk3tTsm51eUZ303nzrimqZWKzopf66lcsMdxd7GknP36VsrfVaZSsWqhOMOvi87DCzEvA986HG/NpJIYZNj0fnAZ4zH0gx9/ze2/w8zCxWNGOh+pFrRRKf99fcXKYa+ZcF5uhtbiYZ9T3Jrb8AAP0avfDO5IXh69ff3Pz/t0wskrj6InVOjoMbfR5zB8WUOuA2q8yCDWuN1ZIiDmvs45LkT99ufWq47a2et/NKmscpx0/rfFrNh733jXlTu28+LcY0t9hXeuyGm7fvfrhC+vz23TLzVt2pfxOMflW0xi3jcM4V1T48FIUrasVuxadYuu81X29JO3pVa4602nd6LC2fVvNB38yLpeWTFFvj+eeS2rekHXMeO+c113zuSFqOMzvlO6oTtL7v26fX+QUbPhilmFKvV1QVU8o6flrns+0VVcWU1oql5ZMUu/f5Nd5XasUON2pFlDsKIpUF7+tznzsSV1SztV6rbMVCdYJRB5+X3XqD3FkxpXfH4/vby1prdTw6D7T3+Pi4SSGTtW09H3rph4lizi0jmXq+ajyXPhr7wx2Fik6n8rwtk9q85H197nNH4n0u26h/o7j1F5hilD+K6Zt5+N5I/TBSW3rUsv/P9z03F8V36tHXNKGYUgdSbiXaQ+w8XmOsEosp9WrbWz3b7buXWOsxSLF13/TSD3MkzeOk2L3Pn/q+0nouTX2/PZ3Ki1+vmNrmrXJ86dbYJbdj7+WrJ3DOFdU+PJSs4gwjx27Fp1i67zVfb0k7elVrjrTad3qs5n6S1eqbkSTN46TYGs8/lzSXtjjHLt3Pvc+t8V6/9PnpMfiIhWofviyl/LB8/GnektgWrzlK7FZ8iqX7XvP1lrSjV7XmSKt9p8dq7idZrb4ZSdI8Toqt8fxzSXNpi3Ps0v3c+9wa7/VLn58eg4+49bcDT7dE/Hyt2BavOUrsPH6Y+fXze/b9eKP+wlrtu7WPkWw5R17qw6R5nHL8rB3rZR7f2zcfCts8v4XxQ5tb36K5taR5nBS79/lT31daHVM/+tEPytdff7eUGb9pulabl7yv33rulu/1e3n/gXOuqALQi9ELeuyxsNDoY5quSf8/LVKnMkdgp1xR7UBKcYY9xM7jNcZKMaX1KKaUdfysv5/3P2Wx7TjfLlry4X/f+imAe/tmD8ep35itc0xNf1/Z/pi6FCu3r6TeNUdaF1Pa8r1+xPcfmMIV1T5s8WX1pC/PJ8VuxadYuu81X29JO3pVa4602nd6LC2fVsfK0r4Z2ejzJu2YuiStfVPy2+o1p1i7X9d+7pznJ8XgRRaqfUgrzjBy7FZ8ihpFLxQquK5lsYekeZx2/PQYW2Jp34xs9HmTdkxdkta+Kflt9ZpTrN2vaz93zvOTYvAiC9UOnE7ldDqVnz+/XWJJbIvXHCV2Kz7F0n2v+XpL2tGrWnOk1b7TY2n5tDpWlvbNyEafN2nH1CVp7ZuS31avOcXa/br2c+c8PykGU/iOKtz2rlwpcPLmzfGj///69TfleLz0SIBJrp5vBqEozg4dDuWrMn1eN5wjH6+hPlQmfvNm0uLK3IYNWKjCDadT+ew8djhcftOaWcUQ4CPH4/GT8w0M4Ooi9XQqM38sZksfp3LrPT0rbxiXW387dTiUw+FQPn+qpDYrtvT5I8fmPvbc0n2v+XpT9zG6Wn2YNI97OH7SY0uM3jfmTT99c0nSMbVFP0zdzxIt+2HtfJLmA5yzUO2XypzbxOY+9lx6dcY9qtWHSfO4h+MnPbbE6H1j3tSLrfH8c0nH1Bb9MHU/S7Tsh7XzSZoP8JHD6eR7zS+59Xt5z39Xr6anT6UeSkn8rcN+Y1MeW2b+/ttLr3frdxsv/ebgPe27tY+pWs31c3OPx7XmyEu/r5k0j5OPn/TYGr+j6rdC9zdv0vqmxvvK1FhZ4T1zzTbfyuft28fnz7mRdt33+hHff1hX4lplDRaqE4w6+NzncOU7qle8u/Q91+dqzK9b++jAu+ff3Wt1PPZwHnh8fLxWtOTdS99/vPHcll7Me21Tx3nOfAjt23PV+5rttDpfHeYVTvrou561jpMXFqCT3PMd1SVj0sP7D22NOkfc+gvzzanul/7HaQ/04XTX+mpKHyb2c2JO9+ihHT3kSL458+j8vbTKHHz9+pulL6HCL1RiodqppV9gr/FF+R5jUx57OpXPnj5NfVVK+X554Tias+97n7tkH3u0RR+mzeN780uT1IdLcu5B8nl3r7E1nn+u4fHz7Xvm6fT+vbTFsfLFFz8tb98+frS9YFLeLc/PSXO21/MfmSxU+7X0C+ytvjyfHlvj+edqPHfJPvZoiz5Mm8f35pcmqQ+X5NyDXs+7I8fWeP4556B5euibpDnbw5jSCQvVfn1ZSvnh079zY0ufP3Jsjeefq/HcJfvYoy36MG0e35tfmqQ+XJJzD3o9744cW+P555yD5umhb5LmbA9jSicUU5pg1C8os57DjAJLr19/U7744qdbpjOce4vYrKmH88BWxTpauqdvOyleFCdlHidpPJcmFbg6XClgdO29Zq1xvrbfa14qQNTyHHSrwNI9hZMuUUyJLY06R1xRnebaF+d9oZ4PJs+Fr7/+7pZ5jMhxVkdiP9+bk0XqfInjn6DlXJq674uPq/Bes6Rw0r2P2cSNAkuOC3ox5FrlO60T6EFiyf6nL6k/lOI369aMLXj+Z+excvu345p4/lttc39btedP5M7dM8Zv367/muv/BuiS/I6fzOFezy0vjVWPav/2ZSfn3V3MpZdyXPv1Zvw+6i13zNfr56Apz0/67di1z889vP/4zdS2Etcqa3BFtV9Lv9Se9CX7pNhWr5kiPb9athjPtHncIr9a++nx2FsqqV9Hnzdpc2ntHHs836Tl06q/lj4/qc3wIt9R7dSon163jq35muXGFdUJ5fA3McIV1TW+h3Hfp+HX++t4PB4S5nHrKwot2jy3H3qVcEVo9HmTOJemnFvKzPeatebSrf2Wu66oLpsjrc9/W+bXw/uPK6pswUIVNnKYUWDpki2KLk0tSvTSc1vqtZjSDgr8TCr8UkNqYaglUo6/vWk9l87H/TCzgFErrT6MXWjTc1jlYncx52NYwq2/sJ1FX2DfoBBG11+of6bXggHxf1wulNS+9Lkw12jt6UnLvr+076Tj7KIbhYnSJfft3HmY3BaYTDGlTo16m1Xr2MqvubjA0pa3KyUUCbnHVp8Sb13Motf+nivjeL6/MNRLt9h9+N8rXGG/+vyE2xQ7Pu/GzKUt+uZ8rjz3/CrmrZ9b2cDdXylJs+2tv0v2e3ke3jqPuM2XEbii2q+HMnbhilaxmvuZIimX0S3tL/39XtLx3OtxkdQPI513e4zdiqdIz2+OVueWLc5Vezx3MhjfUe3UuJ9ej/3Jfpn/kzUbXlHts5jSVpZeaVu7v3vUQ1EPV1TzYmn5JMXO42Vi4SRXVO+z7V1M6xd7SjyPwJosVKGiw8ICS1e8Oz3dZnzNDgr5EGCEDzNaF8/ZgKIqnTrMLJzUaqF6OpVJH+D0ILkgX63XhCRu/YW6tijMMeUPGYtUtqbgTybHfr8mj915AaOKBY3Oj/uezwM95w5DUkxpIG6z6uIWtEmFOcrMW4SXFHEg0z23bbX+HcEtXrP+rb9TRqcvCf06+rxpcBvlzdttP/y0Wf3bP7cpPjXlsVNv25/6ejXPLVvMEbf0MgJXVMfyUBSuWBpLzGeKtV+P9taeN3s8fmocez1I6tfR502teZh03KfNkamSxrTWHHFOpCu+ozoQn16P88l+WbnoUu8FLvbIFdVWV1THO1bSizOl5ZMSO9yuaTCpgFH62O/rimrfxZSgBQtVCPTCHyhTfFRgqfcCF3t0TyEMhTWWG/FYMfbZDjOLJpUyvYDRnsa+52NXMSW4zK2/kGlpUYfzP3oUiYBpRjtWRmvPiOYWvDKmYzGecIViSgNxm9VQt6AtLrr08XM/LXBxz++ohvRNXOze598ag/te7/r4JfdDVqxOMZg93K65r3lzf+zaPCjl/ZXT9OM+ZY70Ugit1i25bvNlBK6ojuWhKFyxNJaWz5y8zy157tLX3FtsjeefS3q90Y+fln1zSVLe5k292DXpx33aHEmXNm967EN2wndUB+LT6/19sl9uF11atcCSK6p1r6gqpjRWLG2skmJp+SSdx6ddUR1/Lk15bC+F0NYck62KKUEKC1Xo2GFe0aVFBZYUZljf2oUwFNboxwZjf60gz7vj8fjZhTgNHGYWTjo9K5p0zZK5dGPesJE1z8XO+YzOrb/QtzlFGPwxAuO6dnw77rPMGY8aRXbMj7oUToIZFFMaiNusdnkL2ieFX8rEAkv3FJ4IaXNc7N7nr10EpXVRlbRxSYptPVatx968mXyb7y2f3Ko55TWXjH0vBYjmeOmW19Fulb5mi9eE2lxRHctDUbhiaSwtn6VtOTf1cXOeL7bO888lvd4ej59afXNJj2Nv3syLXbK0b6a+5tTn9mrkY2XO2G3xmlCV76gOxKfXPtkvL1xRLc8+sVdMqf28UUxpP7Gtx6r12Js3656f511RvX/seylANMeerqgqpsToLFRhMIcZBZZev/6mfPHFTyc9duvCDDsp6vFRYRvFlN4LHPvNCxAZ+/EdNiicdMnUsQ88zjYxoYDUMMfKSG2BS9z6C+OZXKzh66+/u/prLjD8H1BlH228R1q/pOVDnxROqk+xIhiIYkoDcZuVW9CeYrMKLF1y6ZahrfMesajHJVPbvHYfJh8/iWO//a2/6+679dg77168zfeWSbdlTtnP1LFvfZwtvRW1xntNwrxZ6zbdLV4TanNFdSwPReGKpbG0fLZo3xQt+2Z0U9u8dh/2cPwkqdU3a+977dfrYd6kxy7Zom+m7qeVtDmydo5J82ur14SqfEd1IHv/9Non+9dj5cYV1bdvHz+JtbmiOl5Rj0ue9+1oBXXufX7i2K/dX+fx0cbeeXfeebesekV12ti3Ps5yrqj2e6ycxxRTYnQWqrADhxkFlpjrVEo5fBK9VqjqrLjJ1XHZU0GdW3nv0Z7GvkeHmUWSLjndWTjpkl6On5R5ONKxMlJb4BK3/sI+KDCxmct/C1wpVGUcLtMv9GRpUaI9zvc9thlYSDGlwe3pNiu3oN2MLS6wxHwv/57f9efed0vbuq9X7/g5fjI/93wbeY9jv6fz7vWevmrTW17nFknq7fbWqf2wh2Nlzm26W7wm1OaK6vgeyv4KVyyJpeVTq81sY8kYrD2mezx+etXj2I80b9aeX7X6pkY+I82RS5LavHTc93juZDC+ozq4ET697vVT2/RYcUW1hheuqI5VUGeL19zjFdUex36EebPhuXPjK6rz5nv6fNj+imq/x8p5TDElRmehCoEeHx8XF+t4yZs3xy1fnsvenZ5uwy5FMaWt9FJc5pqexr7GuWol747H42e3HnBYoUjSJacXCid11IdLvNj/tYx0nhypLXCJW38h0+Z/tLx+/c2MR3f9d3+Srcf1WsGSvRUy2Vt7W+plgTUlzy3aMmUu9tKHS+yhjcDKFFPaqZTbVtJiKfnMLY5xj0s/nbKl3m6pmhM7j5cbtwZOHef78lm3KFGvx0+Nfph7++Cc5699zuj9XLWWCbf0zrXKOa2nPlwi5dyimJJbf+mHK6r79VByCgEkxRLzGUVSv9aaN5cseVx6LC2fVsfoFnNk7Xz2eK5auy177MMl0s4ta+eYdA7a6jWhKt9R3amkTwOTYin59F4M5hJXVL/1bT+MVNTjUj+0zqfXK6o9FVPq6Vz1Uj+UikWSeu3DJYk+aYUAABUfSURBVJYW92l17Cacb67FFFNidBaqEKj3YjALxBTcWOJwmP5m//r1Nxdvw1YII9vSIiajFNLq4Vz1ox/9oHz99XdXf93TC0WSpuqhD9eQck4bqQDRSG2BS9z6C5n2WgxmlIIbk8dviz+goaL4c9UWx9i8YnQviu/DFeyhjcDKFFPaqZTbVtJiOfncXwym99vIMvp/8bz5ZPzKzNsKk9rX3/FT49bfeWO39Plr55Nwrqo1b8qCW3pvF706bt6H977mrbwvXWlLOKbq3fp7rWey2rz0Nt0tXhNqc0V1vx5KTiGApFhaPkvb0qOkPtxi3kyV1L49Hj9LxnNO30x9/tr5JMVq7meKpH5d4/lTJM2HWnPkkqQ2Lx3jGvMGNuU7qjuV9GlgUiwtnz1eUe2tmMWHvJdc1Xn79nE3/TBKTDGlfuZN2eiKao1+vff5rqiOeaycxxRTYnQWqjCY3gtzjFoA4jCjwNIOvDs93R7dK8WU6jocylel0nfYT8+KJPXar73mXcNIfTNSW+ASt/4CSUYuuDFy2+YapWjWEtfmg3lyWa05o/8BQiimxLdSbmVpGUvL577bmq6Pccrv2I0Wm/jYxQWWRpI0fmsfZ9PmyPIiREvySYpNeez11s1yxy3V118spW/m5t2qLSnvza3HdIu+WbstkMIVVZ57KDnFAVrF0vJZ2pZz+mab2BrP35uk8atxnKXlkxSb+9h79divW+R9SdJ8qHX8XJLU5qVj7D2J7vmOKt9K+oRwhE9t213p2aZQREr7EmP3Pr/s+IpquePqVlJsaTGl1vkk9OHMK6prHCvdFam69/mKKeWO6ZoxxZQYnYUqDGaL4gqPj4/VCplM9O54PHZdjKeUUg4KLD3XVYGltCImaflMdWhUJGmqlv1647z74vkvaT4Evn9socl7UtI4wxbc+gtMkfZHRlo+91K45ZdGGVPmUSTpumt909ux0lu+99hDG6E6C1VuOhzK4XAonz/dGjJ8LC2fpW05t/brtZTW1/c8/3Qqnz1d5XlVSvl+KeXV6VQOvcamPLaXMV37OEvLJyk2073z87Me+3XpvpdoPM7dSTt+jBUjsFDlJUkFA2rE0vJZ2pZza79eS2l9nZRPD/1wSVJb1m5HWj5JsTmScmzZNzXO2y3HuUdJc3Or14SqfEeVm54+YXsogUUEtoil5XNPbItCEbe+B9NKUtGLlvtOik15bLldFCdmTNc+ztLySejD06mcDvO/p121LS37dUmhnLnFlC6p0YcjaXGcKabE6CxUoaKdFJWoYstCEQOOU6tCH5/045s3xzkvEVtgKa2ISVo+5w4rFU26pyDSEo2LKd2976T5kPhB5xYc97A+t/5CXSMtflraujDKaOPUqj2f7Pf1628WPZ9urTGWPRZEYh/j1qqN1/a7hz5nB77TOgH6k3LL2Baxrffz9u3S3u9X8u2H57ERx6nF8XOpH7/44qellI/nQ7lxO3DCfJg7R9LOLQn9dT2791dJE3JM7Nd7973GOWy9try/myP5vbnX2Ic7ZbaYY5DAFVXu8VByinCsHau5n71JGuc9jlPL42dqPq3yXnuOpJ1b0vsrLcekfl267yXS+j8pn6TYGs+HSL6jymwpnyRuEdt6P3spKnFJX1dUxxunGv1/Hp9aiKZ0WGBJMaV5sXJjjLOvqCqmtFX75sTS8kmKrfF8SGWhChXtpajEJT0VdhhxnJILfRxuVH49VS6eM1VaEZO0fM71OMalKKYE0JLvqEJd78o+C8T0VthhtHFK7/+r/X1hgRNbCXiOmpWla3/w8qMf/aB8/fV3pz48fW4C0IiFKlRU4ydCfJK+XIufctmzSwvPG1fgRvkAYZR2fOLWIjX56ikAWRRTYhWHQzkcDuXzp+8/dBtLy2dpW87pm+36OimftH64pNU8bnWczXn+yHo9fqa2pcZ+13j+FGn9n5RPUmzuY6EnFqqsJakCXsvqeUmxS/TNNrG0fNL64ZJW87jVcTbn+SPr9fiZ2pYa+13j+VOk9X9SPkmxuY+FbiimxCqePrF7KAEV8JbE0vK5J7ZVlcqU9iXG0vJJ6Yclc7GEVwJeWvV3xMrSH7x5c7z1n6tXRE48n06JqfrbxxxpHZv7WOiJhSoMxndUSbFkLh5uVIm9oHqBpaXHWVJl6ZnFjxZJ/o5qzQJXlFJKeaceAHCLW38BiPP69TdzHm5xsUCtRWrJr/BrHtWlv4GbLFTZTFKxgS2KEqTHLtE32/V1Uj5p/XDJS6/5xRc/LW/fPn60LXm9Lds8JZc5zx/Iq1LK90spr06ncjidymc9HD/U4xy7PHYrDr2zUGVLScUGtihKkB67RN9sE0vLJ60fLlkyj5e8XqvjbM7zR9Hr8UM9vc6RpNitOHTNd1TZzNMnew8loNjA1FhaPvfEFFMyb1L6YclcvPTcuUV6ko6zOc+v7YV+XWLSmFyLJ5072cbU96RrcbHrfQMjsFCFwSim9N6AhVG6KzyyZC5eeu6tBdVLtwbXlFxMSeGk65IKXO3FxGOl5bm8u/MujMStv8CoRlqkljJee/auSWEhhZNu6jHnnk3t75bnPuddaOg7rRNgXEm3xuzpFs63b7cZk5T2rdEPvUro13m3/t7flp7Hb9rx8/4qTe1bkUvg79PW2s/LsU/HpNffUR0t1lJSP7j1l71xRZUtPZScYgNTY2n5LG3LuT32zUiS+nXOHFnSlh61PH7m5DPlcc6717U8fyX1zejn8aR+WHreha74jiqbSfrEsb9P9usVeRm1b0YsjJJ+FeU8XrOYUtJ3VKcUU2p13BdXVCPOp66ortMPNaT39a049M5CFQYzUjGlAQsiLdLh+N09F+cWU6KU16+/KV988dNv///cwkmnzoof1dDyfDrSuXyJ1gvVPfU1pHHrL5DMIvWXdl/o5fXrb1qnEO18UTqzcNLu59cV1/pFf9XTsq+NMzSkmBJVJd0u09staNNvVdum/9PakuR4PB4Sxr517Dy+djGlD1cLZ9zKynUxtzO23PfLsXWLXt3TN5dk9E2d2Iefh0nJJy0GI3NFldoeSk4BgkuxtHyWtuVcr33Tg6SxTzt+Lll7HjNPD/NG7LqkHM2RtjEYlu+oUlXSp5D9fbLftvhHWluSuKJ67YrqusWULj23uKL6kedFpV74Tq8rquExxZTMkal9A6OyUIXBjFSAo3URjal669da1i6mdOm5h4M/1u5xGqBw0p6LrTnnAHvg1l8gWQ+FLHrIcWT6f75R+myXi1SAvVBMiebSbqFJyue+22W36es27eujiEZaPin9sHYxpSvPNUdevgU6+jbRe5/fS7G1LSSNX/IcGS0Ge+OKKgkeSlZRgqR8lrblnL7ZJpaWT1o/XNJqHqf1Tfpx30Pf7FHS+PUwR0aJwa74jirNpX1amZTPfVcZximm1EssLZ+UfqhRTKl1m1PmSNnlFdU+iq1tocdjIPn46SUGe2OhCoMZqZgSfatRTIn3DjeKSp0GKJx0SS/F1rbgGAD2wK2/MJ5rhVJGKaACfGqPx/3IbQPYPcWUiOT2oiWxbQoQ5bQvL5aWT0o/VCqmFNcPjeZIF0Wl1u2bPoqt3Ru7dcU4Jcf8OdJvDHBFlVwPRcGGtFhaPkmxtHzS+uGSOa9573OTYmn5JMXS8kmKXZOUozmyTQx2z3dUieRT27xYWj5JsbR8UvpBMSVzRN9sc0W1x2PAHHFFFeayUAVgE6MUU3p8fPyqlPK9mvuc4N3x+P7WV8aUdAwAtODWXwC4LW2RWkpmTgCwGgtVunE4lMPhUD5/ukVmk1it/fQYS8snKZaWT1o/XDLnNe997hbtS5I09o6f7frmkqQczZHt2gx7Z6FKT2oVL6ixnx5jafkkxdLySeuHS+a85r3P3aJ9SZLG3vGzTeyapBzNkW1isHu+o0o3nj5pfCgKNjQr7JCUT1IsLZ+UfhilmNKtXFoapaBOWj4pMcWU9j1HAAtVYEWhRWfWpIDNDAMVU4p8o1RQZ2xJxwDLdf7+6L2PJtz6C6yp1zfhqUZv39rezYynSsw3MSfWNcrxw3s9v3/0nDsd+07rBGAJtxdl3Xr19u2c0euTeTNnjrz/BP6+223njcG2sfvbYY7om3tjH65gpeRjjiyL7eH9Edbmiiq9eygKNtSKzX3sqMyb67GtXvNcUpudW5bH0vJJiqXlox/WaQswge+o0jWf2mZ9op1adGZNl4qYlJI1VslzZPrVh5xiSml9M1osLZ+kWFo++mGbc1oPfC+aFixUgdWkFp1ZkzfrOhSSAUbS+/uj8y4tuPUXWNPoRT5Gb18ShWSAkfR87uo5d3p2Op1stqG2Uk6HUk6fl3I6zI0tff7IsbR8kmJp+eiHvFhaPkmxtHySYmn56Id12mKz2aZtzROw2dbent4U/nUpp8/nxpY+f+RYWj5JsbR89ENeLC2fpFhaPkmxtHz0wzptsdls07bmCdhsa2/Fp7abxNLySYql5aMf8mJp+STF0vJJiqXlox/WaYvNZpu2HU6nUwEAAIAUiikBAAAQxUKVXTgcyuFwKJ8//abZ1dicx+4tlpZPUiwtH/2QF0vLJymWlk9SLC0f/TA/b2CB1vce22w1tjKjyMHUx+4tlpZPUiwtH/2QF0vLJymWlk9SLC0f/TA/b5vNdv/WPAGbrcZWdliwYe1YWj5JsbR89ENeLC2fpFhaPkmxtHz0w/y8bTbb/ZtiSgAAAETxHVUAAACiWKiyC6MXbFDMQt8kxNLySYql5ZMUS8snKZaWj34Aqmp977HNVmMrMwofTH3s3mJp+STF0vLRD3mxtHySYmn5JMXS8tEPy/8esdls07fmCdhsNbYyeMGGGrG0fJJiafnoh7xYWj5JsbR8kmJp+eiH5X+P2Gy26ZtiSgAAAETxHVUAAACiWKiyWz0UbEiKpeWTFEvLRz/kxdLySYql5ZMUS8tnpH4AOtD63mObrdVWOijYkBRLyycplpaPfsiLpeWTFEvLJymWls9I/WCz2fK35gnYbK220kHBhqRYWj5JsbR89ENeLC2fpFhaPkmxtHxG6gebzZa/KaYEAABAFN9RBQAAIIqFKtwpqdBEr8UsRoml5aMf8mJp+STF0vJJiqXl00M/AANpfe+xzdbrVoIKTdSIpeWTFEvLRz/kxdLySYql5ZMUS8unh36w2WzjbM0TsNl63UpQoYkasbR8kmJp+eiHvFhaPkmxtHySYmn59NAPNpttnE0xJQAAAKL4jioAAABRLFRhY0kFKRT10Df6Qd+kxdLySYql5VOrzQCllNL83mObbfStBBWkWBJLyycplpaPfsiLpeWTFEvLJymWlk+tNttsNtvpdCrNE7DZRt9KUEGKJbG0fJJiafnoh7xYWj5JsbR8kmJp+dRqs81ms51OiikBAAAQxndUAQAAiGKhCgAAQBQLVQiRVHVR9Ul9ox/0jb5pH0vLZ07eAIu1/pKszWZ7v5WgqouXYmn5JMXS8tEPebG0fJJiafkkxdLymZO3zWazLd2aJ2Cz2d5vJajq4qVYWj5JsbR89ENeLC2fpFhaPkmxtHzm5G2z2WxLN1V/AQAAiOI7qgAAAESxUIUBKOrRNpaWj37Ii6XlkxRLyycp1nrfAE21vvfYZrMt34qiHk1jafnoh7xYWj5JsbR8kmKt922z2Wwtt+YJ2Gy25VtR1KNpLC0f/ZAXS8snKZaWT1Ks9b5tNput5aaYEgAAAFF8RxUAAIAoFqqwI70W9UiPpeWjH/JiafkkxdLySYqt8XyAbrW+99hms9XbSqdFPdJjafnoh7xYWj5JsbR8kmJrPN9ms9l63ZonYLPZ6m2l06Ie6bG0fPRDXiwtn6RYWj5JsTWeb7PZbL1uiikBAAAQxXdUAQAAiGKhCkyWVGQkKZaWj37Ii6XlkxRLyycpBrBrre89ttls/WwlqMhIUiwtH/2QF0vLJymWlk9SzGaz2fa8NU/AZrP1s5WgIiNJsbR89ENeLC2fpFhaPkkxm81m2/OmmBIAAABRfEcVAACAKBaqQBVJBUoUg9EP+iYnlpbP0rYAsJLW9x7bbLZ9bCWoQMnasbR89ENeLC2fpFhaPkvbYrPZbLZ1tuYJ2Gy2fWwlqEDJ2rG0fPRDXiwtn6RYWj5L22Kz2Wy2dTbFlAAAAIjiO6oAAABEsVAFoiQVRtljMRj9oG/23jcAhGh977HNZrM930pQYZSpsbR89ENeLC2fpFhiPjabzWZrvzVPwGaz2Z5vJagwytRYWj76IS+Wlk9SLDEfm81ms7XfFFMCAAAgiu+oAgAAEMVCFRjG6MVgkvRQFCcplpZPUmzuYwHYBwtVYCQPpZQ/efq3ZqzmflK07IceY2n5JMXmPhaAHfAdVWAYT1deHkopX55O5VQrVnM/KVr2Q4+xtHySYnMfC8A+WKgCAAAQxa2/AAAARLFQBSBCUoEfxZTWaTMA3MtCFYAUSQV+FFNaHgOAu/mOKgARkgr8KKY0VvEvAPpjoQoAAEAUt/4CAAAQxUIVgO4lFRHqtZgSACSxUAVgBElFhHotpgQAMXxHFYDuJRUR6rWYEgAksVAFAAAgilt/AQAAiGKhCgBn0oopAcDeWKgCwKfSiikBwK74jioAnEkrpgQAe2OhCgAAQBS3/gIAABDFQhUAAIAoFqoAAABEsVAFAAAgioUqAAAAUSxUAQAAiGKhCgAAQBQLVQAAAKJYqAIAABDFQhUAAIAoFqoAAABEsVAFAAAgioUqAAAAUSxUAQAAiGKhCgAAQBQLVQAAAKJYqAIAABDFQhUAAIAoFqoAAABEsVAFAAAgioUqAAAAUSxUAQAAiGKhCgAAQBQLVQAAAKJYqAIAABDFQhUAAIAoFqoAAABEsVAFAAAgioUqAAAAUSxUAQAAiGKhCgAAQBQLVQAAAKJYqAIAABDFQhUAAIAoFqoAAABEsVAFAAAgioUqAAAAUSxUAQAAiGKhCgAAQBQLVQAAAKJYqAIAABDFQhUAAIAoFqoAAABEsVAFAAAgioUqAAAAUSxUAQAAiGKhCgAAQBQLVQAAAKJYqAIAABDFQhUAAIAoFqoAAABEsVAFAAAgioUqAAAAUSxUAQAAiGKhCgAAQBQLVQAAAKJYqAIAABDFQhUAAIAoFqoAAABEsVAFAAAgioUqAAAAUSxUAQAAiGKhCgAAQBQLVQAAAKJYqAIAABDFQhUAAIAoFqoAAABEsVAFAAAgioUqAAAAUSxUAQAAiPL/AykaYnoisiJNAAAAAElFTkSuQmCC\n",
      "text/plain": [
       "<Figure size 1152x720 with 1 Axes>"
      ]
     },
     "metadata": {
      "needs_background": "light"
     },
     "output_type": "display_data"
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "           A* search search: 154.2 path cost, 7,418 states reached\n"
     ]
    },
    {
     "data": {
      "image/png": "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QlGoAgAAEIpCFQAAgFAUqgAAAISiUAUAACAUhSoAAAChKFQBAAAIRaEKAABAKApVAAAAQlGoAgAAEIpCFQAAgFAUqgAAAISiUAUAACAUhSoAAAChKFQBAAAIRaEKAABAKApVAAAAQlGoAgAAEIpCFQAAgFAUqgAAAISiUAUAACAUhSoAAAChKFQBAAAIRaEKAABAKApVAAAAQlGoAgAAEIpCFQAAgFAUqgAAAISiUAUAACAUhSoAAAChKFQBAAAIRaEKAABAKApVAAAAQlGoAgAAEIpCFQAAgFAUqgAAAISiUAUAACAUhSoAAAChKFQBAAAIRaEKAABAKApVAAAAQlGoAgAAEIpCFQAAgFAUqgAAAISiUAUAACAUhSoAAAChKFQBAAAIRaEKAABAKApVAAAAQlGoAgAAEIpCFQAAgFAUqgAAAISiUAUAACAUhSoAAAChKFQBAAAIRaEKAABAKApVAAAAQlGoAgAAEIpCFQAAgFAUqgAAAISiUAUAACAUhSoAAAChKFQBAAAIRaEKAABAKApVAAAAQlGoAgAAEIpCFQAAgFAUqgAAAISiUAUAACAUhSoAAAChKFQBAAAIRaEKAABAKApVAAAAQlGoAgAAEIpCFQAAgFAUqgAAAISiUAUAACAUhSoAAAChKFQBAAAIRaEKAABAKApVAAAAQlGoAgAAEMr/B8wj0o1qhF8ZAAAAAElFTkSuQmCC\n",
      "text/plain": [
       "<Figure size 1152x720 with 1 Axes>"
      ]
     },
     "metadata": {
      "needs_background": "light"
     },
     "output_type": "display_data"
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "           (b) Weighted (1.4) A* search search: 154.2 path cost, 944 states reached\n"
     ]
    },
    {
     "data": {
      "image/png": "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\n",
      "text/plain": [
       "<Figure size 1152x720 with 1 Axes>"
      ]
     },
     "metadata": {
      "needs_background": "light"
     },
     "output_type": "display_data"
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "           (b) Weighted (2) A* search search: 162.8 path cost, 782 states reached\n"
     ]
    },
    {
     "data": {
      "image/png": "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\n",
      "text/plain": [
       "<Figure size 1152x720 with 1 Axes>"
      ]
     },
     "metadata": {
      "needs_background": "light"
     },
     "output_type": "display_data"
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "           Greedy best-first search search: 164.5 path cost, 448 states reached\n"
     ]
    }
   ],
   "source": [
    "plots(d3)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 47,
   "metadata": {
    "scrolled": false
   },
   "outputs": [
    {
     "data": {
      "image/png": "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AABAKIUoAAAAoRSiAAAAhFKIAgAAEEohCgAAQCiFKAAAAKEUogAAAIRSiAIAABBKIQoAAEAohSgAAAChFKIAAACEUogCAAAQSiEKAABAKIUoAAAAoRSiAAAAhFKIAgAAEEohCgAAQCiFKAAAAKEUogAAAIRSiAIAABBKIQoAAEAohSgAAAChFKIAAACEUogCAAAQSiEKAABAKIUoAAAAoRSiAAAAhFKIAgAAEEohCgAAQCiFKAAAAKEUogAAAIRSiAIAABBKIQoAAEAohSgAAAChFKIAAACEUogCAAAQSiEKAABAKIUoAAAAoRSiAAAAhFKIAgAAEEohCgAAQCiFKAAAAKEUogAAAIRSiAIAABBKIQoAAEAohSgAAAChFKIAAACEUogCAAAQSiEKAABAKIUoAAAAoRSiAAAAhFKIAgAAEEohCgAAQCiFKAAAAKEUogAAAIRSiAIAABBKIQoAAEAohSgAAAChFKIAAACEUogCAAAQSiEKAABAKIUoAAAAoRSiAAAAhFKIAgAAEEohCgAAQCiFKAAAAKEUogAAAIRSiAIAABBKIQoAAEAohSgAAAChFKIAAACEUogCAAAQSiEKAABAKIUoAAAAoRSiAAAAhFKIAgAAEEohCgAAQCiFKAAAAKEUogAAAIRSiAIAABBKIQoAAEAohSgAAAChFKIAAACEUogCAAAQSiEKAABAKIUoAAAAoRSiAAAAhFKIAgAAEEohCgAAQCiFKAAAAKEUogAAAIRSiAIAABBKIQoAAEAohSgAAAChFKIAAACEUogCAAAQSiEKAABAKIUoAAAAoRSiAAAAhFKIAgAAEEohCgAAQCiFKAAAAKEUogAAAIRSiAIAABBKIQoAAEAohSgAAAChFKIAAACEUogCAAAQSiEKAABAKIUoAAAAoRSiAAAAhFKIAgAAEOr/A27LKJSZmrwOAAAAAElFTkSuQmCC\n",
      "text/plain": [
       "<Figure size 1152x720 with 1 Axes>"
      ]
     },
     "metadata": {
      "needs_background": "light"
     },
     "output_type": "display_data"
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "           A* search search: 133.0 path cost, 2,196 states reached\n"
     ]
    },
    {
     "data": {
      "image/png": "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AAilEAUAACCUQhQAAIBQClEAAABCKUQBAAAIpRAFAAAglEIUAACAUApRAAAAQilEAQAACKUQBQAAIJRCFAAAgFAKUQAAAEIpRAEAAAilEAUAACCUQhQAAIBQClEAAABCKUQBAAAIpRAFAAAglEIUAACAUApRAAAAQilEAQAACKUQBQAAIJRCFAAAgFAKUQAAAEIpRAEAAAilEAUAACCUQhQAAIBQClEAAABCKUQBAAAIpRAFAAAglEIUAACAUApRAAAAQilEAQAACKUQBQAAIJRCFAAAgFAKUQAAAEIpRAEAAAilEAUAACCUQhQAAIBQClEAAABCKUQBAAAIpRAFAAAglEIUAACAUApRAAAAQilEAQAACKUQBQAAIJRCFAAAgFAKUQAAAEIpRAEAAAilEAUAACCUQhQAAIBQClEAAABCKUQBAAAIpRAFAAAglEIUAACAUApRAAAAQilEAQAACKUQBQAAIJRCFAAAgFAKUQAAAEIpRAEAAAilEAUAACCUQhQAAIBQClEAAABCKUQBAAAIpRAFAAAglEIUAACAUApRAAAAQilEAQAACKUQBQAAIJRCFAAAgFAKUQAAAEIpRAEAAAilEAUAACCUQhQAAIBQClEAAABCKUQBAAAIpRAFAAAglEIUAACAUApRAAAAQilEAQAACKUQBQAAIJRCFAAAgFAKUQAAAEIpRAEAAAilEAUAACCUQhQAAIBQClEAAABCKUQBAAAIpRAFAAAglEIUAACAUApRAAAAQilEAQAACKUQBQAAIJRCFAAAgFAKUQAAAEIpRAEAAAilEAUAACDU/weM6W3qaeGRAwAAAABJRU5ErkJggg==\n",
      "text/plain": [
       "<Figure size 1152x720 with 1 Axes>"
      ]
     },
     "metadata": {
      "needs_background": "light"
     },
     "output_type": "display_data"
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "           (b) Weighted (1.4) A* search search: 133.0 path cost, 440 states reached\n"
     ]
    },
    {
     "data": {
      "image/png": "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\n",
      "text/plain": [
       "<Figure size 1152x720 with 1 Axes>"
      ]
     },
     "metadata": {
      "needs_background": "light"
     },
     "output_type": "display_data"
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "           (b) Weighted (2) A* search search: 134.2 path cost, 418 states reached\n"
     ]
    },
    {
     "data": {
      "image/png": "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\n",
      "text/plain": [
       "<Figure size 1152x720 with 1 Axes>"
      ]
     },
     "metadata": {
      "needs_background": "light"
     },
     "output_type": "display_data"
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "           Greedy best-first search search: 153.0 path cost, 502 states reached\n"
     ]
    }
   ],
   "source": [
    "plots(d4)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# The cost of weighted A* search\n",
    "\n",
    "Now I want to try a much simpler grid problem, `d6`, with only a few obstacles. We see that A* finds the optimal path, skirting below the obstacles. Weighterd A* with a weight of 1.4 finds the same optimal path while exploring only 1/3 the number of states. But weighted A* with weight 2 takes the slightly longer path above the obstacles, because that path allowed it to stay closer to the goal in straight-line distance, which it over-weights. And greedy best-first search has a bad showing, not deviating from its path towards the goal until it is almost inside the cup made by the obstacles."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 48,
   "metadata": {
    "scrolled": false
   },
   "outputs": [
    {
     "data": {
      "image/png": "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KYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAADYcZriAAABrElEQVQAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKYIqAAAAKf8PLmrpHsltQLwAAAAASUVORK5CYII=\n",
      "text/plain": [
       "<Figure size 1152x720 with 1 Axes>"
      ]
     },
     "metadata": {
      "needs_background": "light"
     },
     "output_type": "display_data"
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "           A* search search: 124.1 path cost, 3,305 states reached\n"
     ]
    },
    {
     "data": {
      "image/png": "iVBORw0KGgoAAAANSUhEUgAAA6oAAAJCCAYAAADJHDpFAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEgAACxIB0t1+/AAAADl0RVh0U29mdHdhcmUAbWF0cGxvdGxpYiB2ZXJzaW9uIDIuMi4zLCBodHRwOi8vbWF0cGxvdGxpYi5vcmcvIxREBQAAGO9JREFUeJzt3T+PXNd9x+HfHSuCo0BrqTKQKnGTwhEoNq4cyG8gMAIDq0KQXTnRq7Cod6E4SOFChQkEAeI+kGBXaSIlDuAudZpIJiHFUGDeFLtkqOXu8s7u3HO/58zzNIKPaJ3D+UPNR3Pvb6d5ngsAAABS7LY+AAAAADxNqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABBFqAIAABDlha0PAACwlvv37z+oqpe3PkdnHp6enp5sfQjguPlGFQAYmUjdn8cM2JxQBQCGMk01TVO9Pk01bX0WAG5GqAIAo7lTVf9w/lcAOiRUAYDRfFJVPzj/KwAdEqoAwFDmueZ5ro/nueatzwLAzQhVAGBkD7c+AAD78+NpAIAunA9HulNVnzz+tvT5a2c/ZuVm/99t19be5+c/v//oNs8HwJp8owoA9OKyIUkjr7XcByDKNM9u3wAA8iV92zn6N6qnp6d+tA+wKaEKAHCE7t+/f+WHQKEKbM2lvwAAAEQRqgDApqappmmq188vS7XW+LEBSCRUAYCtJQ0wSlpruQ9AFPeoAgCbShpglLS29j6G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AEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAEQRqgAAAET5Pzxfqg2F7ogAAAAAAElFTkSuQmCC\n",
      "text/plain": [
       "<Figure size 1152x720 with 1 Axes>"
      ]
     },
     "metadata": {
      "needs_background": "light"
     },
     "output_type": "display_data"
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "           (b) Weighted (1.4) A* search search: 124.1 path cost, 975 states reached\n"
     ]
    },
    {
     "data": {
      "image/png": "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hCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABRhCoAAABR/g/qIHhYi9KlRgAAAABJRU5ErkJggg==\n",
      "text/plain": [
       "<Figure size 1152x720 with 1 Axes>"
      ]
     },
     "metadata": {
      "needs_background": "light"
     },
     "output_type": "display_data"
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "           (b) Weighted (2) A* search search: 128.6 path cost, 879 states reached\n"
     ]
    },
    {
     "data": {
      "image/png": "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FKEKADQhaejImBLAsIQqANCKpKEjY0oAAxKqAEArkoaOjCkBDEioAgBNSBo6MqYEMCyhCgAAQBShCgA0IWnoyJgSwLCEKgDQiqShI2NKAAMSqgBAK5KGjowpAQxIqAIATUgaOjKmBDAsoQoAAEAUoQoANCFp6MiYEsCwhCoA0IqkoSNjSgADEqoAQCuSho6MKQEMqOt776W/zmKx2HiT5vO5l84AwBtYLBYnVfXOoa+D1/n+Btox1VbxjCoAcCgiFYC1hCoAAABRhCoAAABRhCoAAABRhCoAAABRhOp2Tnc8DgBcz/+PZvJ5gbZMslX8eBoAAACieEYVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKEIVAACAKH8DxgVAk+apKx8AAAAASUVORK5CYII=\n",
      "text/plain": [
       "<Figure size 1152x720 with 1 Axes>"
      ]
     },
     "metadata": {
      "needs_background": "light"
     },
     "output_type": "display_data"
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "           Greedy best-first search search: 133.9 path cost, 758 states reached\n"
     ]
    }
   ],
   "source": [
    "plots(d6)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "In the next problem, `d7`, we see a similar story. the optimal path found by A*, and we see that again weighted A* with weight 1.4 does great and with weight 2 ends up erroneously going below the first two barriers, and then makes another mistake by reversing direction back towards the goal and passing above the third barrier. Again, greedy best-first makes bad decisions all around."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 49,
   "metadata": {
    "scrolled": false
   },
   "outputs": [
    {
     "data": {
      "image/png": "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4rm0et20mFvzOD1Lek3TrpEn+V79un5SX/zw+/U//tNP6osf1jD842t/TzjlGdUJer3vO9nxu3P3teVSgj97/mX92Rc/raofVdU/eqe831XVz+oXn39Wv3i+eo0RvQmoJyn31F9fN16ctPUCoqX73dMypZbPJeX9s4fc0sfpcZnSOUmvaco1UvOXLr31z+vv6r/Vv6zv1m9fva67u7t6/Xqo+vuq+tMax7976u/L0/U6qxhUJ+j1xedxb3+S+vtv/+v66Ov3v+D33676nz+q+s//rsodLyzgKYuTzunp88u5wG25DvdreOLSpT8Oqc/qt9+4LfN1Vb2qZ/Xd+ur7htX19fpedusvnHg7pFb96OyQWlX10ddV3/9Z1b/6N1U2snN7FicBsKTZf858r359dkitejNQfKe+qqr6r24D5lYMqkTaainB28VJr+9+XN+83fd9hlVu56aLk87lzlniGGu8T9c4l7V60+K5tHrdtJhb8zhkvfZLXyNTly69m/u39Vd//t367avHhodj/h9U1T+50GaYzKBKqq2WEvygqv6y7l7/w0lVfvR11af/oeqf/XLSl8Mj1ri21zhuT+eyVm9aPJdWr5sWc2seh6zXPu0auf/b+vO/el13ZgdW4xnVCXq97zvZ8TuA97X2ooI//kR1vPvxpGHVs6rcxmLLcyxTysj1dC5L92brepJySx9nL8uUpkp67VOukXdzP6kvfvi8nv/H4fK/ofqqqv5FjeP/ntN7rtPrrGJQnaDXF5/zvvGM6qXbfw2p3MitFied09Pnl3OB23IdMsubZ0//z+uq7537serrqrqr+k1V/UmN46/XLW7fen0v+/E9nBg/H8eq+qyqfla///b5LzKkcjsWJwGQ783w+aev6tl7/7bNH7f+1pt/osaQyk0YVIm09VKCej7e1y8+/6w++vqv682/m/qu39VHX/91vfqnd1XDpAUEPeTS6knKXfnrb7446bFr+1TKUo/Ec1mrNy2eS6vXTYu5NY/DeUnXQ8T7p8b/9d366vt3Vb8Zq179fd39bqx6dVf1G/80DbdmUCXV9ksJfvH8vv74k9XXd/+vqur4359V1WfH/5+yTKGrhQ0N5tLqeazGU632YY1zWas3LZ5Lq9dNi7k1j8N5SddDxvvnzTD6J8/r+V98Wv/9/z6v539Rb273NaRyU55RnaDX+76THb+Ld18BSwneLliq+suq+vc11Gfj5+O4VY1JvZHL741lShm5ns5lT++frXNLH8cypQ9Luh5aeP+wjV5nFYPqBL2++Ex3XLD0g6r65fEZVmhCT59fzgVuy3UIfej1vfytrQuAFhyH019sXQcAAOyBZ1SJtOpigC2XEjSUS6snKZdWz2M1nmq1D2ucy1q9afFcWr1uWsyteRyANAZVUu1nKUE7ubR6knJp9TxW46lW+7DGuazVmxbPpdXrpsXcmscBiOIZ1Ql6ve872fE7vfe186UESbm0epJyafW8m7NMKSPX07ns6f2zdW7p41imBH3odVYxqE7Q64sP9K+nzy/nArflOoQ+9PpedusvAAAAUQyqNKOnxRUt5tLqScql1fNYjada7cMa57JWb1o8l1avmxZzax4HII1BlZb0tLiixVxaPUm5tHoeq/FUq31Y41zW6k2L59LqddNibs3jAETxjOoEvd733Zrjd3/vq+HFFS3n0upJyqXV827OMqWMXE/nsqf3z9a5pY9jmRL0oddZxaA6Qa8vPtC/nj6/nAvclusQ+tDre9mtvwAAAEQxqNKMnhZXtJhLqycpl1bPYzWearUPa5zLWr1p8VxavW5azK15HIA0BlVa0tPiihZzafUk5dLqeazGU632YY1zWas3LZ5Lq9dNi7k1jwMQxTOqE/R633drjt/9va+GF1e0nEurJymXVs+7OcuUMnI9ncue3j9b55Y+jmVK0IdeZxWD6gS9vvhA/3r6/HIucFuuQ+hDr+9lt/4C9O3VzDwAwOYMqjSjp8UVLebS6knKpdXzbu5wODw7HA7Dw8Ph7uHh8OnDw+HucDgMh8PhWat9OCeh10/pTYvn0up102JuzeMApDGo0pKeFle0mEurJymXVk/vfTgnqQ9zetPiubR63bSYW/M4AFE8ozpBr/d9t+b43d/7anhxRcu5tHqScmn19NqHlhcQ9XQurV03LeeWPo5lStCHXmcVg+oEvb74AC3p6bO4p3OhXa5D6EOv72W3/gIAABDFoEozelpc0WIurZ6kXFo9vffhnKQ+zOlNi+fS6nXTYm7N4wCkMajSkp4WV7SYS6snKZdWT+99OCepD3N60+K5tHrdtJhb8zgAUTyjOkGv93235vjd3/tqeHFFy7m0epJyafX02oeWFxD1dC6tXTct55Y+jmVK0IdeZxWD6gS9vvgALenp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AACAKAZVAAAAohhUAQAAiGJQBQAAIIpBFQAAgCgGVQAAAKIYVAEAAIhiUAUAACCKQRUAAIAoBlUAAACiGFQBAACIYlAFAAAgikEVAACAKAZVAAAAohhUAQAAiGJQBQAAIIpBFQAAgCgGVQAAAKIYVAEAAIhiUAUAACCKQRUAAIAoBlUAAACiGFQBAACIYlAFAAAgikEVAACAKAZVAAAAohhUAQAAiGJQBQAAIIpBFQAAgCgGVQAAAKIYVAEAAIhiUAUAACCKQRUAAIAoBlUAAACiGFQBAACIYlAFAAAgikEVAACAKAZVAAAAohhUAQAAiGJQBQAAIIpBFQAAgCgGVQAAAKIYVAEAAIhiUAUAACCKQRUAAIAoBlUAAACiGFQBAACIYlAFAAAgikEVAACAKAZVAAAAohhUAQAAiGJQBQAAIIpBFQAAgCgGVQAAAKIYVAEAAIhiUAUAACCKQRUAAIAoBlUAAACiGFQBAACIYlAFAAAgikEVAACAKAZVAAAAohhUAQAAiGJQBQAAIIpBFQAAgCgGVQAAAKIYVAEAAIhiUAUAACCKQRUAAIAoBlUAAACiGFQBAACIYlAFAAAgikEVAACAKAZVAAAAohhUAQAAiGJQBQAAIIpBFQAAgCgGVQAAAKIYVAEAAIhiUAUAACDK/wcquXLwuqOEZgAAAABJRU5ErkJggg==\n",
      "text/plain": [
       "<Figure size 1152x720 with 1 Axes>"
      ]
     },
     "metadata": {
      "needs_background": "light"
     },
     "output_type": "display_data"
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "           A* search search: 127.4 path cost, 4,058 states reached\n"
     ]
    },
    {
     "data": {
      "image/png": "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iCKoAgAAEEVQBQAAIIqgCgAAQBRBFQAAgCiCKgAAAFEEVQAAAKIIqgAAAEQRVAEAAIgiqAIAABBFUAUAACCKoAoAAEAUQRUAAIAogioAAABRBFUAAACiCKoAAABEEVQBAACIIqgCAAAQRVAFAAAgiqAKAABAFEEVAACAKIIqAAAAUQRVAAAAogiqAAAARBFUAQAAiCKoAgAAEEVQBQAAIIqgCgAAQBRBFQAAgCiCKgAAAFEEVQAAAKIIqgAAAEQRVAEAAIgiqAIAABBFUAUAACCKoAoAAEAUQRUAAIAogioAAABRBFUAAACiCKoAAABEEVQBAACIIqgCAAAQRVAFAAAgiqAKAABAFEEVAACAKIIqAAAAUQRVAAAAogiqAAAARBFUAQAAiCKoAgAAEEVQBQAAIIqgCgAAQBRBFQAAgCiCKgAAAFEEVQAAAKIIqgAAAEQRVAEAAIgiqAIAABBFUAUAACCKoAoAAEAUQRUAAIAogioAAABRBFUAAACiCKoAAABEEVQBAACIIqgCAAAQRVAFAAAgiqAKAABAFEEVAACAKIIqAAAAUQRVAAAAogiqAAAARBFUAQAAiCKoAgAAEEVQBQAAIIqgCgAAQBRBFQAAgCiCKgAAAFEEVQAAAKIIqgAAAEQRVAEAAIgiqAIAABBFUAUAACCKoAoAAEAUQRUAAIAogioAAABRBFUAAACiCKoAAABEEVQBAACIIqgCAAAQRVAFAAAgiqAKAABAFEEVAACAKIIqAAAAUQRVAAAAogiqAAAARBFUAQAAiCKoAgAAEEVQBQAAIIqgCgAAQBRBFQAAgCiCKgAAAFEEVQAAAKIIqgAAAEQRVAEAAIgiqAIAABBFUAUAACCKoAoAAEAUQRUAAIAogioAAABRBFUAAACi/H9tufMPU4+G/wAAAABJRU5ErkJggg==\n",
      "text/plain": [
       "<Figure size 1152x720 with 1 Axes>"
      ]
     },
     "metadata": {
      "needs_background": "light"
     },
     "output_type": "display_data"
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "           (b) Weighted (1.4) A* search search: 127.4 path cost, 1,289 states reached\n"
     ]
    },
    {
     "data": {
      "image/png": "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gioAAABRBFUAAACiCKoAAABEEVQBAACIIqgCAAAQRVAFAAAgiqAKAABAFEEVAACAKIIqAAAAUQRVAAAAogiqAAAARBFUAQAAiCKoAgAAEEVQBQAAIIqgCgAAQBRBFQAAgCiCKgAAAFEEVQAAAKIIqgAAAEQRVAEAAIgiqAIAABBFUAUAACCKoAoAAEAUQRUAAIAogioAAABRBFUAAACiCKoAAABEEVQBAACIIqgCAAAQRVAFAAAgiqAKAABAFEEVAACAKIIqAAAAUQRVAAAAogiqAAAARBFUAQAAiCKoAgAAEEVQBQAAIIqgCgAAQBRBFQAAgCiCKgAAAFEEVQAAAKIIqgAAAEQRVAEAAIgiqAIAABBFUAUAACCKoAoAAEAUQRUAAIAogioAAABRBFUAAACiCKoAAABEEVQBAACIIqgCAAAQRVAFAAAgiqAKAABAFEEVAACAKIIqAAAAUQRVAAAAogiqAAAARBFUAQAAiCKoAgAAEEVQBQAAIIqgCgAAQBRBFQAAgCiCKgAAAFEEVQAAAKIIqgAAAEQRVAEAAIgiqAIAABBFUAUAACCKoAoAAEAUQRUAAIAogioAAABRBFUAAACiCKoAAABEEVQBAACIIqgCAAAQRVAFAAAgiqAKAABAFEEVAACAKIIqAAAAUQRVAAAAogiqAAAARBFUAQAAiCKoAgAAEEVQBQAAIIqgCgAAQBRBFQAAgCiCKgAAAFEEVQAAAKIIqgAAAEQRVAEAAIgiqAIAABBFUAUAACCKoAoAAEAUQRUAAIAogioAAABRBFUAAACiCKoAAABEEVQBAACIIqgCAAAQRVAFAAAgiqAKAABAFEEVAACAKIIqAAAAUQRVAAAAogiqAAAARBFUAQAAiCKoAgAAEEVQBQAAIIqgCgAAQBRBFQAAgCiCKgAAAFEEVQAAAKIIqgAAAEQRVAEAAIgiqAIAABBFUAUAACCKoAoAAEAUQRUAAIAogioAAABRBFUAAACiCKoAAABEEVQBAACIIqgCAAAQRVAFAAAgiqAKAABAlP8DscRvdl+TaAMAAAAASUVORK5CYII=\n",
      "text/plain": [
       "<Figure size 1152x720 with 1 Axes>"
      ]
     },
     "metadata": {
      "needs_background": "light"
     },
     "output_type": "display_data"
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "           (b) Weighted (2) A* search search: 140.4 path cost, 982 states reached\n"
     ]
    },
    {
     "data": {
      "image/png": "iVBORw0KGgoAAAANSUhEUgAAA6oAAAJCCAYAAADJHDpFAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEgAACxIB0t1+/AAAADl0RVh0U29mdHdhcmUAbWF0cGxvdGxpYiB2ZXJzaW9uIDIuMi4zLCBodHRwOi8vbWF0cGxvdGxpYi5vcmcvIxREBQAAG55JREFUeJzt3c+OZHd9xuHvaYw1MfIYVpayilhFCpbxnghxASyIpZ6FE7xIIL4HFh4vuAcCYmFFjjSNIha5ARDsPRZEyjJbbwLMyI5lizlZdM2kpqeq+9TU+fP+Tj2PZBmOq/ucru5q+zPV9XbX930BAABAirOlLwAAAAC2CVUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAAACiCFUAYFW6rrquq292XXUtH0u8HoC5CFUAYG1er6p/3/y95WOJ1wMwi67v+6WvAQBgNJtnAV+vqo/6vvpWjyVeD8BchCoAsFpdVw+q6uWlr6MxD/u+bi99EcBpE6oAwGp1nWcDn0ffe20qsCyvUQUAmmUIaBruV2BpQhUAaJkhoGm4X4FF+dFfAKBZNw0BVdWjBS+vZWdlYAlYkFAFAFbBcNKkDCwBsxKqAMAqrGs4qa8KeymogSVgTi8sfQEAAM/ryo/57nXv3sU8F9S4O3fO9/4zv28VmJMxJQCgZQZ+5mNgCZiNUAUAWvZRVb1ZNzyjyih23dfuf2ASfvQXAGjW5sdN71dVdV5BOant+/q6YwBj8IwqALByXjo51K1bX+z9Z11X/ZW/Hsx4acCJsfoLAKzCdau/FmufdXFxsff+Oj8/f3J/uV+BJXhGFQBoVtdV13X1zc367EG3Sz8253mG3F9Dbzf0bQGuI1QB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AgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEEWoAgAAEOX/AIS6zUzgLYR1AAAAAElFTkSuQmCC\n",
      "text/plain": [
       "<Figure size 1152x720 with 1 Axes>"
      ]
     },
     "metadata": {
      "needs_background": "light"
     },
     "output_type": "display_data"
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "           Greedy best-first search search: 151.6 path cost, 826 states reached\n"
     ]
    }
   ],
   "source": [
    "plots(d7)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Nondeterministic Actions\n",
    "\n",
    "To handle problems with nondeterministic problems, we'll replace the `result` method with `results`, which returns a collection of possible result states. We'll represent the solution to a problem not with a `Node`, but with a plan that consist of two types of component: sequences of actions, like `['forward', 'suck']`, and condition actions, like\n",
    "`{5: ['forward', 'suck'], 7: []}`, which says that if we end up in state 5, then do `['forward', 'suck']`, but if we end up in state 7, then do the empty sequence of actions."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 50,
   "metadata": {},
   "outputs": [],
   "source": [
    "def and_or_search(problem):\n",
    "    \"Find a plan for a problem that has nondterministic actions.\"\n",
    "    return or_search(problem, problem.initial, [])\n",
    "    \n",
    "def or_search(problem, state, path):\n",
    "    \"Find a sequence of actions to reach goal from state, without repeating states on path.\"\n",
    "    if problem.is_goal(state): return []\n",
    "    if state in path: return failure # check for loops\n",
    "    for action in problem.actions(state):\n",
    "        plan = and_search(problem, problem.results(state, action), [state] + path)\n",
    "        if plan != failure:\n",
    "            return [action] + plan\n",
    "    return failure\n",
    "\n",
    "def and_search(problem, states, path):\n",
    "    \"Plan for each of the possible states we might end up in.\"\n",
    "    if len(states) == 1: \n",
    "        return or_search(problem, next(iter(states)), path)\n",
    "    plan = {}\n",
    "    for s in states:\n",
    "        plan[s] = or_search(problem, s, path)\n",
    "        if plan[s] == failure: return failure\n",
    "    return [plan]"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 51,
   "metadata": {},
   "outputs": [],
   "source": [
    "class MultiGoalProblem(Problem):\n",
    "    \"\"\"A version of `Problem` with a colllection of `goals` instead of one `goal`.\"\"\"\n",
    "    \n",
    "    def __init__(self, initial=None, goals=(), **kwds): \n",
    "        self.__dict__.update(initial=initial, goals=goals, **kwds)\n",
    "        \n",
    "    def is_goal(self, state): return state in self.goals\n",
    "    \n",
    "class ErraticVacuum(MultiGoalProblem):\n",
    "    \"\"\"In this 2-location vacuum problem, the suck action in a dirty square will either clean up that square,\n",
    "    or clean up both squares. A suck action in a clean square will either do nothing, or\n",
    "    will deposit dirt in that square. Forward and backward actions are deterministic.\"\"\"\n",
    "    \n",
    "    def actions(self, state): \n",
    "        return ['suck', 'forward', 'backward']\n",
    "    \n",
    "    def results(self, state, action): return self.table[action][state]\n",
    "    \n",
    "    table = {'suck':{1:{5,7}, 2:{4,8}, 3:{7}, 4:{2,4}, 5:{1,5}, 6:{8}, 7:{3,7}, 8:{6,8}},\n",
    "             'forward': {1:{2}, 2:{2}, 3:{4}, 4:{4}, 5:{6}, 6:{6}, 7:{8}, 8:{8}},\n",
    "             'backward': {1:{1}, 2:{1}, 3:{3}, 4:{3}, 5:{5}, 6:{5}, 7:{7}, 8:{7}}}"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Let's find a plan to get from state 1 to the goal of no dirt (states 7 or 8):"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 52,
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "['suck', {5: ['forward', 'suck'], 7: []}]"
      ]
     },
     "execution_count": 52,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "and_or_search(ErraticVacuum(1, {7, 8}))"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "This plan says \"First suck, and if we end up in state 5, go forward and suck again; if we end up in state 7, do nothing because that is a goal.\"\n",
    "\n",
    "Here are the plans to get to a goal state starting from any one of the 8 states:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 53,
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "{1: ['suck', {5: ['forward', 'suck'], 7: []}],\n",
       " 2: ['suck', {8: [], 4: ['backward', 'suck']}],\n",
       " 3: ['suck'],\n",
       " 4: ['backward', 'suck'],\n",
       " 5: ['forward', 'suck'],\n",
       " 6: ['suck'],\n",
       " 7: [],\n",
       " 8: []}"
      ]
     },
     "execution_count": 53,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "{s: and_or_search(ErraticVacuum(s, {7,8})) \n",
    " for s in range(1, 9)}"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Comparing Algorithms on EightPuzzle Problems of Different Lengths"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 54,
   "metadata": {},
   "outputs": [],
   "source": [
    "from functools import lru_cache\n",
    "\n",
    "def build_table(table, depth, state, problem):\n",
    "    if depth > 0 and state not in table:\n",
    "        problem.initial = state\n",
    "        table[state] = len(astar_search(problem))\n",
    "        for a in problem.actions(state):\n",
    "            build_table(table, depth - 1, problem.result(state, a), problem)\n",
    "    return table\n",
    "\n",
    "def invert_table(table):\n",
    "    result = defaultdict(list)\n",
    "    for key, val in table.items():\n",
    "        result[val].append(key)\n",
    "    return result\n",
    "\n",
    "goal = (0, 1, 2, 3, 4, 5, 6, 7, 8)\n",
    "table8 = invert_table(build_table({}, 25, goal, EightPuzzle(goal)))"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 78,
   "metadata": {
    "scrolled": false
   },
   "outputs": [
    {
     "data": {
      "text/plain": [
       "2.6724"
      ]
     },
     "execution_count": 78,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "def report8(table8, M, Ds=range(2, 25, 2), searchers=(breadth_first_search, astar_misplaced_tiles, astar_search)):\n",
    "    \"Make a table of average nodes generated and effective branching factor\"\n",
    "    for d in Ds:\n",
    "        line = [d]\n",
    "        N = min(M, len(table8[d]))\n",
    "        states = random.sample(table8[d], N)\n",
    "        for searcher in searchers:\n",
    "            nodes = 0\n",
    "            for s in states:\n",
    "                problem = CountCalls(EightPuzzle(s))\n",
    "                searcher(problem)\n",
    "                nodes += problem._counts['result']\n",
    "            nodes = int(round(nodes/N))\n",
    "            line.append(nodes)\n",
    "        line.extend([ebf(d, n) for n in line[1:]])\n",
    "        print('{:2} & {:6} & {:5} & {:5} && {:.2f} & {:.2f} & {:.2f}'\n",
    "              .format(*line))\n",
    "\n",
    "        \n",
    "def ebf(d, N, possible_bs=[b/100 for b in range(100, 300)]):\n",
    "    \"Effective Branching Factor\"\n",
    "    return min(possible_bs, key=lambda b: abs(N - sum(b**i for i in range(1, d+1))))\n",
    "\n",
    "def edepth_reduction(d, N, b=2.67):\n",
    "    \n",
    "    \n",
    "\n",
    "from statistics import mean \n",
    "\n",
    "def random_state():\n",
    "    x = list(range(9))\n",
    "    random.shuffle(x)\n",
    "    return tuple(x)\n",
    "\n",
    "meanbf = mean(len(e3.actions(random_state())) for _ in range(10000))\n",
    "meanbf"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 72,
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "{0: 1,\n",
       " 1: 2,\n",
       " 2: 4,\n",
       " 3: 8,\n",
       " 4: 16,\n",
       " 5: 20,\n",
       " 6: 36,\n",
       " 7: 60,\n",
       " 8: 87,\n",
       " 9: 123,\n",
       " 10: 175,\n",
       " 11: 280,\n",
       " 12: 397,\n",
       " 13: 656,\n",
       " 14: 898,\n",
       " 15: 1452,\n",
       " 16: 1670,\n",
       " 17: 2677,\n",
       " 18: 2699,\n",
       " 19: 4015,\n",
       " 20: 3472,\n",
       " 21: 4672,\n",
       " 22: 3311,\n",
       " 23: 3898,\n",
       " 24: 1945,\n",
       " 25: 1796,\n",
       " 26: 621,\n",
       " 27: 368,\n",
       " 28: 63,\n",
       " 29: 19,\n",
       " 30: 0}"
      ]
     },
     "execution_count": 72,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "{n: len(v) for (n, v) in table30.items()}"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 67,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "CPU times: user 24min 7s, sys: 11.6 s, total: 24min 19s\n",
      "Wall time: 24min 44s\n"
     ]
    }
   ],
   "source": [
    "%time table30 = invert_table(build_table({}, 30, goal, EightPuzzle(goal)))"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 68,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      " 2 &      5 &     6 &     6 && 1.79 & 2.00 & 2.00\n",
      " 4 &     33 &    12 &    12 && 2.06 & 1.49 & 1.49\n",
      " 6 &    128 &    24 &    19 && 2.01 & 1.42 & 1.34\n",
      " 8 &    368 &    48 &    31 && 1.91 & 1.40 & 1.30\n",
      "10 &   1033 &   116 &    48 && 1.85 & 1.43 & 1.27\n",
      "12 &   2672 &   279 &    84 && 1.80 & 1.45 & 1.28\n",
      "14 &   6783 &   678 &   174 && 1.77 & 1.47 & 1.31\n",
      "16 &  17270 &  1683 &   364 && 1.74 & 1.48 & 1.32\n",
      "18 &  41558 &  4102 &   751 && 1.72 & 1.49 & 1.34\n",
      "20 &  91493 &  9905 &  1318 && 1.69 & 1.50 & 1.34\n",
      "22 & 175921 & 22955 &  2548 && 1.66 & 1.50 & 1.34\n",
      "24 & 290082 & 53039 &  5733 && 1.62 & 1.50 & 1.36\n",
      "CPU times: user 6min, sys: 3.63 s, total: 6min 4s\n",
      "Wall time: 6min 13s\n"
     ]
    }
   ],
   "source": [
    "%time report8(table30, 20, range(26, 31, 2))"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 70,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "26 & 395355 & 110372 & 10080 && 1.58 & 1.50 & 1.35\n",
      "28 & 463234 & 202565 & 22055 && 1.53 & 1.49 & 1.36\n"
     ]
    },
    {
     "ename": "ZeroDivisionError",
     "evalue": "division by zero",
     "output_type": "error",
     "traceback": [
      "\u001b[0;31m---------------------------------------------------------------------------\u001b[0m",
      "\u001b[0;31mZeroDivisionError\u001b[0m                         Traceback (most recent call last)",
      "\u001b[0;32m<timed eval>\u001b[0m in \u001b[0;36m<module>\u001b[0;34m()\u001b[0m\n",
      "\u001b[0;32m<ipython-input-69-674fb01939fb>\u001b[0m in \u001b[0;36mreport8\u001b[0;34m(table8, M, Ds, searchers)\u001b[0m\n\u001b[1;32m     11\u001b[0m                 \u001b[0msearcher\u001b[0m\u001b[0;34m(\u001b[0m\u001b[0mproblem\u001b[0m\u001b[0;34m)\u001b[0m\u001b[0;34m\u001b[0m\u001b[0m\n\u001b[1;32m     12\u001b[0m                 \u001b[0mnodes\u001b[0m \u001b[0;34m+=\u001b[0m \u001b[0mproblem\u001b[0m\u001b[0;34m.\u001b[0m\u001b[0m_counts\u001b[0m\u001b[0;34m[\u001b[0m\u001b[0;34m'result'\u001b[0m\u001b[0;34m]\u001b[0m\u001b[0;34m\u001b[0m\u001b[0m\n\u001b[0;32m---> 13\u001b[0;31m             \u001b[0mnodes\u001b[0m \u001b[0;34m=\u001b[0m \u001b[0mint\u001b[0m\u001b[0;34m(\u001b[0m\u001b[0mround\u001b[0m\u001b[0;34m(\u001b[0m\u001b[0mnodes\u001b[0m\u001b[0;34m/\u001b[0m\u001b[0mN\u001b[0m\u001b[0;34m)\u001b[0m\u001b[0;34m)\u001b[0m\u001b[0;34m\u001b[0m\u001b[0m\n\u001b[0m\u001b[1;32m     14\u001b[0m             \u001b[0mline\u001b[0m\u001b[0;34m.\u001b[0m\u001b[0mappend\u001b[0m\u001b[0;34m(\u001b[0m\u001b[0mnodes\u001b[0m\u001b[0;34m)\u001b[0m\u001b[0;34m\u001b[0m\u001b[0m\n\u001b[1;32m     15\u001b[0m         \u001b[0mline\u001b[0m\u001b[0;34m.\u001b[0m\u001b[0mextend\u001b[0m\u001b[0;34m(\u001b[0m\u001b[0;34m[\u001b[0m\u001b[0mebf\u001b[0m\u001b[0;34m(\u001b[0m\u001b[0md\u001b[0m\u001b[0;34m,\u001b[0m \u001b[0mn\u001b[0m\u001b[0;34m)\u001b[0m \u001b[0;32mfor\u001b[0m \u001b[0mn\u001b[0m \u001b[0;32min\u001b[0m \u001b[0mline\u001b[0m\u001b[0;34m[\u001b[0m\u001b[0;36m1\u001b[0m\u001b[0;34m:\u001b[0m\u001b[0;34m]\u001b[0m\u001b[0;34m]\u001b[0m\u001b[0;34m)\u001b[0m\u001b[0;34m\u001b[0m\u001b[0m\n",
      "\u001b[0;31mZeroDivisionError\u001b[0m: division by zero"
     ]
    }
   ],
   "source": [
    "%time report8(table30, 20, range(26, 31, 2))"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 315,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "0 116 116 ['A']\n",
      "140 0 140 ['A', 'S']\n",
      "0 83 83 ['A']\n",
      "118 0 118 ['A', 'T']\n",
      "0 45 45 ['A']\n",
      "75 0 75 ['A', 'Z']\n",
      "0 176 176 ['B']\n",
      "101 92 193 ['B', 'P']\n",
      "211 0 211 ['B', 'F']\n",
      "0 77 77 ['B']\n",
      "90 0 90 ['B', 'G']\n",
      "0 100 100 ['B']\n",
      "101 0 101 ['B', 'P']\n",
      "0 80 80 ['B']\n",
      "85 0 85 ['B', 'U']\n",
      "0 87 87 ['C']\n",
      "120 0 120 ['C', 'D']\n",
      "0 109 109 ['C']\n",
      "138 0 138 ['C', 'P']\n",
      "0 128 128 ['C']\n",
      "146 0 146 ['C', 'R']\n",
      "0 47 47 ['D']\n",
      "75 0 75 ['D', 'M']\n",
      "0 62 62 ['E']\n",
      "86 0 86 ['E', 'H']\n",
      "0 98 98 ['F']\n",
      "99 0 99 ['F', 'S']\n",
      "0 77 77 ['H']\n",
      "98 0 98 ['H', 'U']\n",
      "0 85 85 ['I']\n",
      "87 0 87 ['I', 'N']\n",
      "0 78 78 ['I']\n",
      "92 0 92 ['I', 'V']\n",
      "0 36 36 ['L']\n",
      "70 0 70 ['L', 'M']\n",
      "0 86 86 ['L']\n",
      "111 0 111 ['L', 'T']\n",
      "0 136 136 ['O']\n",
      "151 0 151 ['O', 'S']\n",
      "0 48 48 ['O']\n",
      "71 0 71 ['O', 'Z']\n",
      "0 93 93 ['P']\n",
      "97 0 97 ['P', 'R']\n",
      "0 65 65 ['R']\n",
      "80 0 80 ['R', 'S']\n",
      "0 127 127 ['U']\n",
      "142 0 142 ['U', 'V']\n"
     ]
    },
    {
     "data": {
      "text/plain": [
       "(1.2698088530709188, 1.2059558858330393)"
      ]
     },
     "execution_count": 315,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "from itertools import combinations\n",
    "from statistics import median, mean\n",
    "\n",
    "# Detour index for Romania\n",
    "\n",
    "L = romania.locations\n",
    "def ratio(a, b): return astar_search(RouteProblem(a, b, map=romania)).path_cost / sld(L[a], L[b])\n",
    "nums = [ratio(a, b) for a,b in combinations(L, 2) if b in r1.actions(a)]\n",
    "mean(nums), median(nums) # 1.7, 1.6 # 1.26, 1.2 for adjacent cities"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 300,
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "<function __main__.straight_line_distance(A, B)>"
      ]
     },
     "execution_count": 300,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "sld"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": []
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.7.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}
