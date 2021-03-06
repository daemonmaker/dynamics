'''
Class using keras to model the classic pendulum dynamics in OpenAI gym.
'''
import numpy as np

import keras.backend as KK
from keras.models import Model
from keras.layers import Input, Lambda
from keras.layers.merge import Concatenate

from dynamics import Dynamics


def pendulum_dynamics(x_combined):
    x = x_combined[:, :2]
    u = x_combined[:, 2:]
    g = 10.
    l = 1.
    pi = np.pi
    m = 1.
    deltaT = 0.05
    th = x[0, 0]
    thdot = x[0, 1]
    newthdot = thdot + (-3*g/(2*l) * KK.sin(th + pi) + 3./(m*KK.square(l))*u)*deltaT
    newth = th + newthdot*deltaT
    new_x = KK.concatenate([newth, newthdot])
    return new_x


def pendulum_cost(x_combined):
    x = x_combined[:, :2]
    u = x_combined[:, 2:]
    th = x[0, 0]
    thdot = x[0, 1]
    normalized_th = KK.mod((th+np.pi), (2*np.pi)) - np.pi
    return (
        KK.square(normalized_th)
        + 0.1*KK.square(thdot)
        + 0.001*KK.square(u)
    )

def pendulum_goal_generator():
    return np.matrix([[
        2*np.pi*np.random.randint(-3, 4),
        0.0
    ]], dtype='float32')


def pendulum_goal_checker(x):
    if x.shape[0] == 2:
        import ipdb; ipdb.set_trace()
    return (
        1.0-np.cos(x[0, 0]) <= np.finfo('float32').eps
        and x[0, 1] == 0
    )


class Pendulum(Dynamics):
    def __init__(self, x_dim, u_dim, r_dim):
        super(Pendulum, self).__init__(x_dim, u_dim, r_dim)
        self.x_dim = x_dim
        self.u_dim = u_dim
        self.r_dim = r_dim

        x_data = np.asmatrix([[1, 1], [2, 2]])
        u_data = np.asmatrix([[1], [2]])

        x_in = Input(shape=(2,))
        u_in = Input(shape=(1,))
        combined_inputs = Concatenate()([x_in, u_in])
        model = Model(
            [x_in, u_in],
            [
                Lambda(lambda x: pendulum_dynamics(x))(combined_inputs),
                Lambda(lambda x: pendulum_cost(x))(combined_inputs)
            ]
        )
        print("predict: ", model.predict([x_data, u_data]))

        self.mdl = model


    def compare_to_gym(self, time_steps=1000):
        import gym

        env = gym.make('Pendulum-v0')
        obs_t = np.expand_dims(env.reset(), axis=1)
        x_t = np.expand_dims(env.state, axis=1)

        total_state_diff = 0
        total_loss_diff = 0

        for tidx in np.arange(time_steps):
            u_t = env.action_space.sample()
            env_res = env.step(u_t)
            env_obs_t1 = env_res[0]
            env_x_t1 = env.state
            env_loss_t = env_res[1]

            k_res = self.mdl.predict([
                x_t.T,
                np.expand_dims(u_t, axis=0)
            ])
            k_x_t1 = k_res[0]
            k_loss_t = k_res[1]

            state_diff = np.sum(np.square(
                np.squeeze(env_x_t1) - np.squeeze(k_x_t1)
            ))
            loss_diff = np.sum(np.square(
                np.squeeze(env_loss_t) + np.squeeze(k_loss_t)
            ))
            print("tidx: ", tidx)
            print("\tState diff: ", state_diff)
            print("\tloss diff: ", loss_diff)

            if state_diff >= np.finfo('float32').eps:
                print("~~~~~~~~~~~~~~~~~~~~~ Flag state ~~~~~~~~~~~~~")
                print("env_x_t1: ", env_x_t1)
                print("k_x_t1: ", k_x_t1)
                total_state_diff += state_diff

            if loss_diff >= np.finfo('float32').eps:
                print("#################### Flag loss ###############")
                print("env_loss_t: ", env_loss_t)
                print("k_loss_t: ", k_loss_t)
                total_loss_diff += loss_diff


            obs_t = env_obs_t1
            x_t = env_x_t1
            loss_t = env_loss_t

        print("Total state diff: ", total_state_diff)
        print("Total loss diff: ", total_loss_diff)


    def compare_to_gym_batched(self, batch_size, time_steps=1000):
        import gym

        env = gym.make('Pendulum-v0')

        o_t = env.reset()
        x_t = env.state

        total_us = batch_size*time_steps
        us = np.zeros((total_us,))
        for tidx in np.arange(total_us):
            us[tidx] = env.action_space.sample()
        us = us.reshape(batch_size, time_steps)


        obs = np.zeros((batch_size, time_steps, o_t.shape[0]))
        xs = np.zeros((batch_size, time_steps, x_t.shape[0]))

        obs[0, 0] = o_t
        xs[0, 0] = x_t

        obs_t = np.expand_dims(env.reset(), axis=1)
        x_t = np.expand_dims(env.state, axis=0)

        total_state_diff = 0
        total_loss_diff = 0

        for tidx in np.arange(time_steps):
            u_t = env.action_space.sample()
            env_res = env.step(u_t)
            env_obs_t1 = env_res[0]
            env_x_t1 = env.state
            env_loss_t = env_res[1]

            print "tidx: ", tidx
            print x_t.shape, ' ', x_t
            print u_t.shape, ' ', np.expand_dims(u_t, axis=0), ' ', np.expand_dims(u_t, axis=0).shape
            k_res = self.mdl.predict([
                x_t,
                np.expand_dims(u_t, axis=0)
            ])
            k_x_t1 = k_res[0]
            k_loss_t = k_res[1]

            state_diff = np.sum(np.square(
                np.squeeze(env_x_t1) - np.squeeze(k_x_t1)
            ))
            loss_diff = np.sum(np.square(
                np.squeeze(env_loss_t) + np.squeeze(k_loss_t)
            ))
            print("tidx: ", tidx)
            print("\tState diff: ", state_diff)
            print("\tloss diff: ", loss_diff)

            if state_diff >= np.finfo('float32').eps:
                print("~~~~~~~~~~~~~~~~~~~~~ Flag state ~~~~~~~~~~~~~")
                print("env_x_t1: ", env_x_t1)
                print("k_x_t1: ", k_x_t1)
                total_state_diff += state_diff

            if loss_diff >= np.finfo('float32').eps:
                print("#################### Flag loss ###############")
                print("env_loss_t: ", env_loss_t)
                print("k_loss_t: ", k_loss_t)
                total_loss_diff += loss_diff


            obs_t = env_obs_t1
            x_t = np.expand_dims(env_x_t1, axis=0)
            loss_t = env_loss_t

        print("Total state diff: ", total_state_diff)
        print("Total loss diff: ", total_loss_diff)


def test():
    pendulum = Pendulum(x_dim=2, u_dim=1, r_dim=1)

    pendulum.compare_to_gym_batched(batch_size=1)
    pendulum.compare_to_gym_batched(batch_size=2)

