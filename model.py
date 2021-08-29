# 2021 Nathan Nguyen
# Source: Patrick Loeber - https://github.com/python-engineer/snake-ai-pytorch
#
# Deep Q Learning Model

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import os

class Linear_QNet(nn.Module):

  # input_size - size of state space
  # hidden_size - for hidden layer
  # output_size - number of possible actions
  def __init__(self, input_size, hidden_size, output_size):
    super().__init__()
    self.linear1 = nn.Linear(input_size, hidden_size)
    self.linear2 = nn.Linear(hidden_size, output_size)

  def forward(self, x):
    x = F.relu(self.linear1(x))
    x = self.linear2(x)
    return x

  def save(self, file_name="model.pth"):
    model_folder_path = "./model"
    if not os.path.exists(model_folder_path):
      os.makedirs(model_folder_path)

    file_name = os.path.join(model_folder_path, file_name)
    torch.save(self.state_dict(), file_name)

class QTrainer:

  def __init__(self, model, lr, gamma):
    self.lr = lr
    self.gamma = gamma
    self.model = model
    self.optimizer = optim.Adam(model.parameters(), lr=self.lr)
    self.criterion = nn.MSELoss()

    # learning rate decay
    self.scheduler = optim.lr_scheduler.StepLR(self.optimizer, step_size=5000, gamma=0.75)

  def train_step(self, state, action, reward, next_state, game_over):
    state = torch.tensor(state, dtype=torch.float)
    next_state = torch.tensor(next_state, dtype=torch.float)
    action = torch.tensor(action, dtype=torch.long)
    reward = torch.tensor(reward, dtype=torch.float)

    if len(state.shape) == 1:
      state = torch.unsqueeze(state, 0)
      next_state = torch.unsqueeze(next_state, 0)
      action = torch.unsqueeze(action, 0)
      reward = torch.unsqueeze(reward, 0)
      game_over = (game_over, )

    # predicted Q values for current state
    pred = self.model(state)

    target = pred.clone()
    for i in range(len(game_over)):
      Q_new = reward[i]
      if not game_over[i]:
        Q_new = reward[i] + self.gamma * torch.max(self.model(next_state[i]))

      target[i][torch.argmax(action).item()] = Q_new

    # r + y * max(next predicted Q)
    # perform if not already done
    self.optimizer.zero_grad()
    loss = self.criterion(target, pred)
    loss.backward()

    self.optimizer.step()
    self.scheduler.step()
