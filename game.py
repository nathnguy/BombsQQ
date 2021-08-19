# Copyright 2021 Nathan Nguyen
#
# CONCEPT:
# On a grid, there are two bombs (red), two civilians(green), and one player(blue).
# When the timer runs out, the bombs blow up the surrounding area.
# By this time, the player must find the civilians and leave the danger area.

import pygame
import random
from enum import Enum
from collections import namedtuple

pygame.init()
font = pygame.font.SysFont('arial', 18)

Point = namedtuple('Point', 'x, y')

# rgb colors
BLUE = (77, 186, 240)
RED = (246, 62, 80)
GREEN = (57, 212, 98)
BACKGROUND = (31, 39, 55)
WHITE = (255, 255, 255)
GRID = (136, 255, 142)
PURPLE = (161, 60, 255)

BLOCK_SIZE = 50

# frame rate
SPEED = 30

# number of each item
NUM_BOMBS = 2
NUM_BONUSES = 2

BOMB_RADIUS = 2

# time per round in milliseconds
TOTAL_TIME = 3000

class Direction(Enum):
  RIGHT = 1
  LEFT = 2
  UP = 3
  DOWN = 4

class Game:

  def __init__(self, w=350, h=350):
    self.w = w
    self.h = h

    # display preferences
    self.display = pygame.display.set_mode((self.w, self.h))
    pygame.display.set_caption('Bombs QQ')
    self.clock = pygame.time.Clock()

    # game state

    # player location
    location = Point((self.w / 2) - (BLOCK_SIZE / 2),
      (self.h / 2) - (BLOCK_SIZE / 2))

    # locations for bombs, bonuses, and player
    # first NUM_BOMBS entries are bombs
    # next NUM_BONUSES entries are bonuses (civilians)
    # player is always the last entry
    self.locations = [None, None, None, None, location]
    
    self.direction = None
    self.score = 0
    self.timer = TOTAL_TIME

    # number of collected bonuses
    self.num_collected = 0

    self._place_items()

  # places items in random locations
  def _place_items(self):
    self.locations = [None, None, None, None, self._get_player_loc()]
    for i in range(4):
      new_loc = None

      # search for location that does not overlap with other element
      while new_loc in self.locations:
        x = random.randint(0, (self.w // BLOCK_SIZE) - 1) * BLOCK_SIZE
        y = random.randint(0, (self.h // BLOCK_SIZE) - 1) * BLOCK_SIZE
        new_loc = Point(x, y)

      # save new unique location
      self.locations[i] = new_loc

  # returns the player's current location
  def _get_player_loc(self):
    return self.locations[len(self.locations) - 1]

  # executes every frame
  def play_step(self):
    game_over = False

    # get user input
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        pygame.quit()
        quit()

      if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_w or event.key == pygame.K_UP:
          self.direction = Direction.UP
        elif event.key == pygame.K_a or event.key == pygame.K_LEFT:
          self.direction = Direction.LEFT
        elif event.key == pygame.K_s or event.key == pygame.K_DOWN:
          self.direction = Direction.DOWN
        elif event.key == pygame.K_d or event.key == pygame.K_RIGHT:
          self.direction = Direction.RIGHT
        elif event.key == pygame.K_SPACE:
          self._place_items()
      # elif event.type == pygame.KEYUP:
      #   self.direction = None

    self._move()
    self._check_bonus()

    game_over = self._check_time()
    self._update_ui()
    self.clock.tick(SPEED)

    return game_over, self.score

  # decrements timer and checks for winning round
  # returns true iff game is lost
  def _check_time(self):
    self.timer -= self.clock.get_time()

    if self.timer <= 0:
      self.timer = 0
      if self.num_collected == NUM_BONUSES and\
        not self._near_bomb(self._get_player_loc()):
        # won round, reset
        self.score += 1
        self.timer = TOTAL_TIME
        self.num_collected = 0
        self._place_items()
        return False
      # lost round
      return True
    
    return False


  # checks if player is on bonus
  def _check_bonus(self):
    for i in range(NUM_BOMBS, NUM_BOMBS + NUM_BONUSES):
      if self.locations[i] != None and\
        self.locations[i].x == self._get_player_loc().x and\
        self.locations[i].y == self._get_player_loc().y:
        self.num_collected += 1
        self.locations[i] = None


  # moves the player
  def _move(self):
    x = self._get_player_loc().x
    y = self._get_player_loc().y

    if self.direction == Direction.UP and y > 0:
      y -= BLOCK_SIZE
    elif self.direction == Direction.LEFT and x > 0:
      x -= BLOCK_SIZE
    elif self.direction == Direction.DOWN and y < (self.h - BLOCK_SIZE):
      y += BLOCK_SIZE
    elif self.direction == Direction.RIGHT and x < (self.w - BLOCK_SIZE):
      x += BLOCK_SIZE

    # can't move into bomb
    for i in range(NUM_BOMBS):
      if x == self.locations[i].x and y == self.locations[i].y:
        # revert to original position
        x = self._get_player_loc().x
        y = self._get_player_loc().y

    # update location
    self.locations[len(self.locations) - 1] = Point(x, y)
    self.direction = None

  def _update_ui(self):
    self.display.fill(BACKGROUND)

    # player
    pygame.draw.rect(self.display, BLUE, pygame.Rect(self._get_player_loc().x, self._get_player_loc().y,
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
        if self._near_bomb(curr_point):
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
  def _near_bomb(self, loc):
    for bomb_loc in self.locations[0:NUM_BOMBS]:
      x_dist = abs(bomb_loc.x - loc.x)
      y_dist = abs(bomb_loc.y - loc.y)
      if x_dist <= (BLOCK_SIZE * BOMB_RADIUS) and y_dist <= (BLOCK_SIZE * BOMB_RADIUS):
        return True
    return False

if __name__ == '__main__':
  game = Game()

  # main game loop
  while True:
    game_over, score = game.play_step()

    if game_over:
      break

  print("Completed " + str(score) + " round(s)!")

  pygame.quit()

