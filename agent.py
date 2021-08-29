# 2021 Nathan Nguyen
# Source: Patrick Loeber - https://github.com/python-engineer/snake-ai-pytorch
#
# Run this file to train the reinforcement learning model. Includes an agent that records
# the game state and chooses actions through deep Q learning. Individual and mean game scores
# are plotted as the agent trains.

import torch
import random
import numpy as np
from collections import deque
from game import Game, Direction, Point
from model import Linear_QNet, QTrainer
from helper import plot

MAX_MEMORY = 100_000
BATCH_SIZE = 1000
LR = 0.0007  # learning rate

BLOCK_SIZE = 50
GRID_SIZE = 7

class Agent:

  def __init__(self):
    self.n_games = 0
    self.epsilon = 0  # for randomness
    self.gamma = 0.9  # discount rate (<1)

    # pops left when max memory reached
    self.memory = deque(maxlen=MAX_MEMORY)
    
    self.model = Linear_QNet(19, 256, 5)
    self.trainer = QTrainer(self.model, lr=LR, gamma=self.gamma)

    # uncomment to load saved model at given path
    # self.model.load_state_dict(torch.load("./model/model_v2.pth"))

  # state:
  #   - danger at player position
  #   - is the bonus collected
  #   - is there a safe spot left, right, down, up
  #   - is the player next to a bomb or wall
  #   - current movement direction 
  #   - is there a bonus to the left, right, down, or up directions
  def get_state(self, game):
    curr_pos = game.get_player_loc()
    bonus1 = game.locations[2]
    
    # points left, right, down, up
    pl = Point(curr_pos.x - BLOCK_SIZE, curr_pos.y)
    pr = Point(curr_pos.x + BLOCK_SIZE, curr_pos.y)
    pd = Point(curr_pos.x, curr_pos.y + BLOCK_SIZE)
    pu = Point(curr_pos.x, curr_pos.y - BLOCK_SIZE)

    # safe_left, safe_right, safe_down, safe_up = self._safe_spots(game)
    safe_left, safe_right, safe_down, safe_up = self._safe_straight(game)

    state = [
      # danger
      game.near_bomb(curr_pos),

      game.num_collected == 1,  # bonus collected

      # safe spots
      safe_left, safe_right, safe_down, safe_up,

      # next to bomb or wall
      game.has_bomb(pl) or curr_pos.x == 0,
      game.has_bomb(pr) or curr_pos.x == game.w - BLOCK_SIZE ,
      game.has_bomb(pd) or curr_pos.y == game.h - BLOCK_SIZE,
      game.has_bomb(pu) or curr_pos.y == 0,

      # movement
      game.direction == None,
      game.direction == Direction.LEFT,
      game.direction == Direction.RIGHT,
      game.direction == Direction.DOWN,
      game.direction == Direction.UP,

      # bonus position
      (bonus1 != None and bonus1.x < curr_pos.x),
      (bonus1 != None and bonus1.x > curr_pos.x),
      (bonus1 != None and bonus1.y > curr_pos.y),
      (bonus1 != None and bonus1.y < curr_pos.y)
    ]

    return np.array(state, dtype=int)

  # returns true iff there is a safe space directly
  # left, right, down, and up from the player
  def _safe_straight(self, game):
    left = False
    right = False
    down = False
    up = False

    player_pos = game.get_player_loc()
    x = int(player_pos.x / BLOCK_SIZE)
    y = int(player_pos.y / BLOCK_SIZE)

    # left
    for i in range(0, x):
      pt = Point(i * BLOCK_SIZE, y * BLOCK_SIZE)
      if not game.near_bomb(pt):
        left = True
        break

    # right
    for i in range(x + 1, GRID_SIZE):
      pt = Point(i * BLOCK_SIZE, y * BLOCK_SIZE)
      if not game.near_bomb(pt):
        right = True
        break

    # down
    for i in range(y + 1, GRID_SIZE):
      pt = Point(x * BLOCK_SIZE, i * BLOCK_SIZE)
      if not game.near_bomb(pt):
        down = True
        break

    # up
    for i in range(0, y):
      pt = Point(x * BLOCK_SIZE, i * BLOCK_SIZE)
      if not game.near_bomb(pt):
        up = True
        break

    return left, right, down, up

  def remember(self, state, action, reward, next_state, game_over):
    self.memory.append((state, action, reward, next_state, game_over))

  def train_long_memory(self):
    if len(self.memory) > BATCH_SIZE:
      mini_sample = random.sample(self.memory, BATCH_SIZE)  # list of tuples
    else:
      mini_sample = self.memory

    states, actions, rewards, next_states, game_overs = zip(*mini_sample)
    self.trainer.train_step(states, actions, rewards, next_states, game_overs)

  def train_short_memory(self, state, action, reward, next_state, game_over):
    self.trainer.train_step(state, action, reward, next_state, game_over)

  # action: 
  # [1, 0, 0, 0 ,0] - stay
  # [0, 1, 0, 0 ,0] - left
  # [0, 0, 1, 0 ,0] - right
  # [0, 0, 0, 1 ,0] - down
  # [0, 0, 0, 0 ,1] - up
  def get_action(self, state):
    # random moves for start (tradeoff exploration vs. exploitation)
    self.epsilon = 150 - self.n_games
    final_move = [0, 0, 0, 0, 0]

    if random.randint(0, 230) < self.epsilon:
      move = random.randint(0, len(final_move) - 1)
      final_move[move] = 1
    else:
      state0 = torch.tensor(state, dtype=torch.float)
      prediction = self.model(state0)
      move = torch.argmax(prediction).item()
      final_move[move] = 1

    return final_move

def train():
  plot_scores = []
  plot_mean_scores = []
  total_score = 0
  record = 0
  agent = Agent()
  game = Game()

  while True:
    # get old state
    state_old = agent.get_state(game)

    # move based on current state
    final_move = agent.get_action(state_old)

    # execute move then get new state
    game_over, score, reward = game.play_step(final_move)
    state_new = agent.get_state(game)

    # train short memory
    agent.train_short_memory(state_old, final_move, reward, state_new, game_over)

    # remember, store in memory
    agent.remember(state_old, final_move, reward, state_new, game_over)

    if game_over:
      # train long memory (experience replay)
      game.reset()
      agent.n_games += 1
      agent.train_long_memory()

      if score > record:
        agent.model.save()
        record = score

      print("Game", agent.n_games, "Score", score, "Record:", record)

      plot_scores.append(score)
      total_score += score
      mean_score = total_score / agent.n_games
      plot_mean_scores.append(mean_score)
      plot(plot_scores, plot_mean_scores)

if __name__ == "__main__":
  train()