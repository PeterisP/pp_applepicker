# encoding=utf-8
import numpy as np
from itertools import count
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torch.autograd as autograd
from torch.autograd import Variable
from torch.utils.data import TensorDataset, DataLoader

gamma, seed, batch = 0.99, 543, 1
#D = 105*80
D=60*80
episode_length = 20

# valid_actions = ['i','j','l',',','p']
valid_actions = ['i','j','l','p']
torch.manual_seed(seed)

class Policy(nn.Module):
    def __init__(self):
        super(Policy, self).__init__()
        self.affine1 = nn.Linear(D, 50)
        nn.init.xavier_normal(self.affine1.weight)
        self.affine2 = nn.Linear(50, len(valid_actions))
        nn.init.xavier_normal(self.affine2.weight)

        self.saved_actions = []
        self.rewards = []

    def forward(self, x):
        x = F.relu(self.affine1(x))
        action_scores = self.affine2(x)
        return F.softmax(action_scores)

policy = Policy()
# policy.cuda()
optimizer = optim.RMSprop(policy.parameters(), lr=1e-3)

# Pagaidām (priekš Atari) sagaida 210 x 160 krāsainu attēlu
# in 480x640x3
# out 60x80x1
def prepro(I):    
  I = I[::8,::8,1] # downsample by factor of 2, choose colour 2 to improve visibility in other games   
  # I[I == 17] = 0 # erase background (background type 1)   
  # I[I == 192] = 0 # erase background (background type 2)   
  # I[I == 136] = 0 # erase background (background type 3)   
  # I[I != 0] = 1 # everything else (paddles, ball) just set to 1
  I = (I-128)/128
  # plt.imshow(I) 
  # plt.show()
  return I.astype(np.float).ravel() # 2D array to 1D array (vector)


def run_episodic_learning(env_reset, env_step):
    running_reward = None 
    for episode_number in count(1):
        observation = env_reset() 
        # observation, reward, done, _ = env_step('j')
        prev_x = None # used in computing the difference frame    
        reward_sum = 0  
         
        for t in range(episode_length): # Don't infinite loop while learning
            cur_x = prepro(observation)   
            state = cur_x - prev_x if prev_x is not None else np.zeros(D)   
            prev_x = cur_x  

            state = torch.from_numpy(state).float().unsqueeze(0)
            # probs = policy(Variable(state).cuda())
            probs = policy(Variable(state))
            # actiong = probs.multinomial()
            m = torch.distributions.Categorical(probs)
            actiong = m.sample()
            action = actiong.data
            policy.saved_actions.append(m.log_prob(actiong))
            
            observation, reward, done, _ = env_step(valid_actions[action[0]])
            reward_sum += reward 
            policy.rewards.append(reward)

            if done:
                break

        accumulate = min([episode_number, 10])
        running_reward = reward_sum if running_reward is None else running_reward * (1.0-1.0/accumulate) + reward_sum * (1.0/accumulate)
        print ('episode: {}, reward: {}, mean reward: {:3f}'.format(episode_number, reward_sum, running_reward))
        
        if episode_number % batch == 0:
            print('Episode {}\tLast length: {:5d}\tAverage length: {:.2f}'.format(
                episode_number, t, running_reward))
            # finish_episode()

            R = 0
            rewards = []
            loss = []
            for r in policy.rewards[::-1]:
                # if r != 0: R = 0 # reset the sum, since this was a game boundary (pong specific!)
                R = r + gamma * R
                rewards.insert(0, R)
#print (rewards)
            rewards = torch.Tensor(rewards) # .cuda()
            # rewards = (rewards - rewards.mean()) # / (rewards.std() + np.finfo(np.float32).eps)
            # tmp = rewards.std()
            # if tmp > 0.0 : rewards /= tmp #fixed occasional zero-divide
            for action, r in zip(policy.saved_actions, rewards):
                # action.reinforce(r)
                loss.append(-action * r)
            optimizer.zero_grad()
            loss = torch.cat(loss).sum()
            # autograd.backward(policy.saved_actions, [None for _ in policy.saved_actions])
            # loss.backward(policy.saved_actions, [None for _ in policy.saved_actions])
            loss.backward()
            optimizer.step()

            del policy.rewards[:]
            del policy.saved_actions[:]

