# import gym
import numpy as np
from itertools import count
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torch.autograd as autograd
from torch.autograd import Variable
from torch.utils.data import TensorDataset, DataLoader
# import npickle
# import types
# import matplotlib.pyplot as plt
# %matplotlib inline

gamma, seed, batch = 0.99, 543, 10
D = 105*80

def _step_custom(self, a):
    env = self.unwrapped or self
    action = env._action_set[a]
    num_steps = 4 #self.np_random.randint(2, 5)
    ob = []; reward = 0.0
    for _ in range(num_steps):
        reward += env.ale.act(action)
        ob.append(env._get_obs())
    ob = np.maximum.reduce(ob) # returns max pixel values from 4 frames
    return ob, reward, env.ale.game_over(), {"ale.lives": env.ale.lives()} # lives left

#env = gym.make("PongDeterministic-v3")
env = gym.make("Pong-v3")
#env = gym.make("SpaceInvaders-v3") # environment info
env.seed(seed)
torch.manual_seed(seed)
env.unwrapped._step = types.MethodType(_step_custom, env)
valid_actions = range(env.action_space.n) #number of valid actions in the specific game   
print ('action count:', env.action_space.n) 

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
policy.cuda()
optimizer = optim.RMSprop(policy.parameters(), lr=1e-3)

def prepro(I):    
  I = I[::2,::2,2] # downsample by factor of 2, choose colour 2 to improve visibility in other games   
  I[I == 17] = 0 # erase background (background type 1)   
  I[I == 192] = 0 # erase background (background type 2)   
  I[I == 136] = 0 # erase background (background type 3)   
  I[I != 0] = 1 # everything else (paddles, ball) just set to 1 
  # plt.imshow(I) 
  # plt.show()
  return I.astype(np.float).ravel() # 2D array to 1D array (vector)   

def immitate5():
    dtype = torch.FloatTensor
    print ('Immitation learning DNN from the Episodic memory with Pytorch')
    memoryScr = npickle.load_gzip('XmemoryScrZ.k')
    print ('Screens are loaded', len(memoryScr))
    memoryAct = npickle.load_gzip('XmemoryActZ.k')
    print ('Actions are loaded', len(memoryAct))
    memoryScr = np.array(memoryScr[-200000:]) ; print ("memoryScr", len(memoryScr))
    memoryAct = np.array(memoryAct[-200000:]) ; print ("memoryAct", len(memoryAct))
    memoryScr = torch.from_numpy(memoryScr).type(dtype).cuda() ; print ("memoryScr", len(memoryScr))
    memoryAct = torch.from_numpy(memoryAct).type(dtype).cuda() ; print ("memoryAct", len(memoryAct))
    print(type(memoryScr))
    print(type(memoryAct))
    loader = DataLoader(TensorDataset(memoryScr,memoryAct), batch_size = 3200)
    criterion = torch.nn.MSELoss(size_average=False)
    optimizer2 = torch.optim.Adam(policy.parameters(), lr=1e-4)    #0.0001)
    lgraphx, lgraphy, lgraphyA, lgraphyB, lgraphyC =[],[], [],[], [] 
    step = 0
    for epoch in range(1000):
        for x_batch, y_batch in loader:
            x_var, y_var = Variable(x_batch).cuda(), Variable(y_batch).cuda()
            y_pred = policy(x_var)
            loss2 = criterion(y_pred,y_var)
            step += 1
            lgraphx.append(step)
            lgraphy.append(loss2.data.cpu().numpy())
            optimizer2.zero_grad()
            loss2.backward()
            optimizer2.step()
            #print ("minibatch")
        print ("epoch", epoch, step, lgraphy[-1])
        plt.plot(lgraphx, lgraphy)
        plt.show()   
 
def immitate():
    dtype = torch.FloatTensor
    print ('Immitation learning DNN from the Episodic memory with Pytorch')
    memoryScr = npickle.load_gzip('XmemoryScrZ.k')
    print ('Screens are loaded', len(memoryScr))
    memoryAct = npickle.load_gzip('XmemoryActZ.k')
    print ('Actions are loaded', len(memoryAct))
    memoryScr = np.array(memoryScr[-200000:]) ; print ("memoryScr", len(memoryScr))
    memoryAct = np.array(memoryAct[-200000:]) ; print ("memoryAct", len(memoryAct))
    memoryScr = torch.from_numpy(memoryScr).type(dtype).cuda() ; print ("Torch memoryScr", len(memoryScr))
    memoryAct = torch.from_numpy(memoryAct).type(dtype).cuda() ; print ("Torch memoryAct", len(memoryAct))
    print(type(memoryScr))
    print(type(memoryAct))
    loader = DataLoader(TensorDataset(memoryScr,memoryAct), batch_size=3200, shuffle=True, drop_last=True)
    criterion = torch.nn.MSELoss(size_average=False)
    optimizer2 = torch.optim.Adam(policy.parameters(), lr=1e-4)    #0.0001)
    lgraphx, lgraphy, lgraphyA, lgraphyB, lgraphyC =[],[], [],[], [] 
    step = 0
    for epoch in range(30002):
        for x_batch, y_batch in loader:
            x_var, y_var = Variable(x_batch).cuda(), Variable(y_batch).cuda()
            y_pred = policy(x_var)
            loss2 = criterion(y_pred,y_var)
            step += 1
            lgraphx.append(step)
            lgraphy.append(loss2.data.cpu().numpy())
            optimizer2.zero_grad()
            loss2.backward()
            optimizer2.step()
            #print ("minibatch")     
        if epoch % 100 == 0:            
            print ("epoch", epoch, step, lgraphy[-1])
            plt.plot(lgraphx, lgraphy)
            plt.show()   
 
    

def finish_episode():
    R = 0
    rewards = []
    for r in policy.rewards[::-1]:
        if r != 0: R = 0 # reset the sum, since this was a game boundary (pong specific!)   
        R = r + gamma * R
        rewards.insert(0, R)
    #print (rewards)
    rewards = torch.Tensor(rewards).cuda()
    rewards = (rewards - rewards.mean()) # / (rewards.std() + np.finfo(np.float32).eps)  
    tmp = rewards.std()  
    if tmp > 0.0 : rewards /= tmp #fixed occasional zero-divide   
    for action, r in zip(policy.saved_actions, rewards):
        action.reinforce(r)
    optimizer.zero_grad()
    autograd.backward(policy.saved_actions, [None for _ in policy.saved_actions])
    optimizer.step()
    del policy.rewards[:]
    del policy.saved_actions[:]

immitate()
running_reward = None 
lgraphx, lgraphy = [], [] #used for plotting graph 
for episode_number in count(1):
    observation = env.reset()
    prev_x = None # used in computing the difference frame    
    reward_sum = 0  
     
    for t in range(10000): # Don't infinite loop while learning
        cur_x = prepro(observation)   
        state = cur_x - prev_x if prev_x is not None else np.zeros(D)   
        prev_x = cur_x  

        state = torch.from_numpy(state).float().unsqueeze(0)
        probs = policy(Variable(state).cuda())
        actiong = probs.multinomial()
        policy.saved_actions.append(actiong)
        action = actiong.data
        
        observation, reward, done, _ = env.step(action[0,0])
        reward_sum += reward 
        policy.rewards.append(reward)

        if done:
            break

    accumulate = min([episode_number, 10])
    running_reward = reward_sum if running_reward is None else running_reward * (1-1/accumulate) + reward_sum * (1/accumulate)
    print ('episode: {}, reward: {}, mean reward: {:3f}'.format(episode_number, reward_sum, running_reward))
    lgraphx.append(episode_number)
    lgraphy.append(running_reward)
    
    if episode_number % batch == 0:
        print('Episode {}\tLast length: {:5d}\tAverage length: {:.2f}'.format(
            episode_number, t, running_reward))
        plt.plot(lgraphx, lgraphy)   
        plt.show() 
        finish_episode()

