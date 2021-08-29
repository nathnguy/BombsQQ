# 2021 Nathan Nguyen
#
# CONCEPT:
# On a grid, there are two bombs (red), one civilian (green), and one player (blue).
# When the timer runs out, the bombs blow up the surrounding area.
# By this time, the player must find the civilians and leave the danger area.
#
# Run this file to play BombsQQ.
# Controls: move with the WASD or arrow keys

import pygame
import random
from enum import Enum
from collections import namedtuple
import numpy as np

pygame.init()
font = pygame.font.SysFont("arial", 18)

# Defines a square on the grid. The top left square is (0,0) while the bottom right
# is (6,6)
Point = namedtuple("Point", "x, y")

# RGB colors
BLUE = (77, 186, 240)
RED = (246, 62, 80)
GREEN = (57, 212, 98)
BACKGROUND = (31, 39, 55)
WHITE = (255, 255, 255)
GRID = (136, 255, 142)
PURPLE = (161, 60, 255)

BLOCK_SIZE = 50
GRID_SIZE = 7

# frame rate
SPEED = 30

# number of each item
NUM_BOMBS = 2
NUM_BONUSES = 1  # changing this will break training state implementation

BOMB_RADIUS = 2

# time per round in milliseconds
TOTAL_TIME = 2000

# actions determined by agent
ACTION_STAY = [1, 0, 0, 0, 0]
ACTION_LEFT = [0, 1, 0, 0, 0]
ACTION_RIGHT = [0, 0, 1, 0, 0]
ACTION_DOWN = [0, 0, 0, 1, 0]
ACTION_UP = [0, 0, 0, 0, 1]

# Describes the player's movement.
class Direction(Enum):
  RIGHT = 1
  LEFT = 2
  UP = 3
  DOWN = 4

class Game:

  def __init__(self, w=350, h=350, training=True):
    self.w = w
    self.h = h
    self.training = training  # false when game is human controlled

    # display preferences
    self.display = pygame.display.set_mode((self.w, self.h))
    pygame.display.set_caption("BombsQQ")
    self.clock = pygame.time.Clock()

    # initializes game state
    self.reset()

  # resets game to original state
  def reset(self):
    # player location in center of grid

    # locations for bombs, bonuses, and player
    # first NUM_BOMBS entries are bombs
    # next NUM_BONUSES entries are bonuses (civilians)
    # player is always the last entry
    location = Point((self.w / 2) - (BLOCK_SIZE / 2),
      (self.h / 2) - (BLOCK_SIZE / 2))
    self.locations = [None] * (NUM_BOMBS + NUM_BONUSES)
    self.locations.append(location)
    
    self.direction = None
    self.score = 0
    self.timer = TOTAL_TIME

    # number of collected bonuses
    self.num_collected = 0

    self._place_items()

  # places items in random locations
  def _place_items(self):
    player_loc = self.get_player_loc()
    self.locations = [None] * (NUM_BOMBS + NUM_BONUSES)
    self.locations.append(player_loc)
    for i in range(len(self.locations) - 1):
      new_loc = None

      # search for location that does not overlap with other element
      while new_loc in self.locations:
        x = random.randint(0, (self.w // BLOCK_SIZE) - 1) * BLOCK_SIZE
        y = random.randint(0, (self.h // BLOCK_SIZE) - 1) * BLOCK_SIZE
        new_loc = Point(x, y)

      # save new unique location
      self.locations[i] = new_loc

    # try again if the grid is in an illegal state:
    # all three items (2 bombs and player/bonus) are in a
    # corner and the corner element is a bonus or the player
    redo = False
    for i in range(NUM_BOMBS, len(self.locations)):
      if self._is_blocked(self.locations[i]):
        redo = True
        break

    if redo:
      self._place_items()

  # returns true if the point is surrounded by bombs/walls
  def _is_blocked(self, pt):
    surrounding = [Point(pt.x - BLOCK_SIZE, pt.y),
                  Point(pt.x + BLOCK_SIZE, pt.y),
                  Point(pt.x, pt.y - BLOCK_SIZE),
                  Point(pt.x, pt.y + BLOCK_SIZE)]

    for square in surrounding:
      if not (self.has_bomb(square) or square.x < 0 or
        square.x >= self.w or square.y < 0 or square.y >= self.h):
        return False

    return True

  # returns true iff there is a bomb at the given point
  def has_bomb(self, pt):
    for i in range(0, NUM_BOMBS):
      if self.locations[i] == pt:
        return True

    return False

  # returns the player's current location
  def get_player_loc(self):
    return self.locations[-1]

  # executes every frame
  def play_step(self, action):
    game_over = False

    # get user input
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        pygame.quit()
        quit()

      if not self.training and event.type == pygame.KEYDOWN:
        if event.key == pygame.K_w or event.key == pygame.K_UP:
          self.direction = Direction.UP
        elif event.key == pygame.K_a or event.key == pygame.K_LEFT:
          self.direction = Direction.LEFT
        elif event.key == pygame.K_s or event.key == pygame.K_DOWN:
          self.direction = Direction.DOWN
        elif event.key == pygame.K_d or event.key == pygame.K_RIGHT:
          self.direction = Direction.RIGHT

    move_reward = self._move(action)
    bonus_reward = self._check_bonus()

    game_over, reward = self._check_time()
    reward += bonus_reward
    reward += move_reward
    self._update_ui()
    self.clock.tick(SPEED)

    return game_over, self.score, reward

  # decrements timer and checks for winning round
  # returns true iff game is lost and the reward
  def _check_time(self):
    reward = 0
    self.timer -= self.clock.get_time()

    if self.timer <= 0:
      self.timer = 0

      # reward for ending on a safe square
      if not self.near_bomb(self.get_player_loc()):
        reward += 5

      if (self.num_collected == NUM_BONUSES and
        not self.near_bomb(self.get_player_loc())):
        # won round, reset
        self.score += 1
        self.timer = TOTAL_TIME
        self.num_collected = 0
        self._place_items()
        reward += 10
        return False, reward
      # lost round
      reward -= 20
      return True, reward
    
    return False, reward


  # checks if player is on bonus
  # returns reward for getting bonus
  def _check_bonus(self):
    reward = 0
    for i in range(NUM_BOMBS, NUM_BOMBS + NUM_BONUSES):
      if self.locations[i] != None and\
        self.locations[i].x == self.get_player_loc().x and\
        self.locations[i].y == self.get_player_loc().y:
        self.num_collected += 1
        self.locations[i] = None
        reward += 10

    return reward


  # moves the player
  def _move(self, action):
    reward = 0

    if self.training:
      # AI controlled direction
      if np.array_equal(action, ACTION_STAY):
        self.direction = None
      elif np.array_equal(action, ACTION_LEFT):
        self.direction = Direction.LEFT
      elif np.array_equal(action, ACTION_RIGHT):
        self.direction = Direction.RIGHT
      elif np.array_equal(action, ACTION_DOWN):
        self.direction = Direction.DOWN
      elif np.array_equal(action, ACTION_UP):
        self.direction = Direction.UP

    x = self.get_player_loc().x
    y = self.get_player_loc().y

    if self.direction == Direction.UP:
      y -= BLOCK_SIZE
    elif self.direction == Direction.LEFT:
      x -= BLOCK_SIZE
    elif self.direction == Direction.DOWN:
      y += BLOCK_SIZE
    elif self.direction == Direction.RIGHT:
      x += BLOCK_SIZE

    # can't move past grid boundaries or into bomb
    if (y < 0 or y >= self.h or
      x < 0 or x >= self.w or self.has_bomb(Point(x, y))):
      x = self.get_player_loc().x
      y = self.get_player_loc().y
      reward = -5

    # update location
    self.locations[-1] = Point(x, y)

    if not self.training:
      self.direction = None

    return reward

  def _update_ui(self):
    self.display.fill(BACKGROUND)

    # player
    pygame.draw.rect(self.display, BLUE, pygame.Rect(self.get_player_loc().x, self.get_player_loc().y,
      BLOCK_SIZE, BLOCK_SIZE))

    # bombs
    for i in range(NUM_BOMBS):
      pygame.draw.rect(self.display, RED, pygame.Rect(self.locations[i].x, self.locations[i].y,
        BLOCK_SIZE, BLOCK_SIZE))

    # bonuses
    for i in range(NUM_BOMBS, NUM_BOMBS + NUM_BONUSES):
      if self.locations[i] != None:
        pygame.draw.rect(self.display, GREEN, pygame.Rect(self.locations[i].x, self.locations[i].y,
          BLOCK_SIZE, BLOCK_SIZE))

    # grid
    for x in range(self.w // BLOCK_SIZE):
      for y in range(self.h // BLOCK_SIZE):
        curr_point = Point(x * BLOCK_SIZE, y * BLOCK_SIZE)

        color = GRID
        if self.near_bomb(curr_point):
          color = RED
        
        pygame.draw.rect(self.display, color, pygame.Rect(curr_point.x, curr_point.y,
          BLOCK_SIZE, BLOCK_SIZE), 1)

    # text

    # timer
    timer_txt = font.render("Detonating in: " + str(self.timer / 1000) + "s", True, WHITE)
    self.display.blit(timer_txt, [10, 10])

    # score
    score_txt = font.render("Score: " + str(self.score), True, WHITE)
    self.display.blit(score_txt, [self.w - (BLOCK_SIZE * 2) + 10, 10])

    pygame.display.flip()

  # returns true iff give location is touching a bomb
  def near_bomb(self, loc):
    for bomb_loc in self.locations[0:NUM_BOMBS]:
      x_dist = abs(bomb_loc.x - loc.x)
      y_dist = abs(bomb_loc.y - loc.y)
      if x_dist <= (BLOCK_SIZE * BOMB_RADIUS) and y_dist <= (BLOCK_SIZE * BOMB_RADIUS):
        return True
    return False

if __name__ == "__main__":
  game = Game(training=False)

  # main game loop
  while True:
    game_over, score, reward = game.play_step([])

    if game_over:
      break

  print("Completed " + str(score) + " round(s)!")

  pygame.quit()

