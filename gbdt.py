import json
import lightgbm as lgb
import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error
from sklearn.linear_model import LogisticRegression

from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

li = load_iris()

# sklearn.model_selection.train_test_split(*arrays, **options)
# x	       数据集的特征值
# y         数据集的标签值
# test_size           测试集的大小，一般为float
# random_state        随机数种子,不同的种子会造成不同的随机采样结果。相同的种子采样结果相同。
# return  训练集特征值，测试集特征值，训练标签，测试标签(默认随机取)

x_train, x_test, y_train, y_test = train_test_split(li.data, li.target, test_size=0.25)
print("训练集特征值和目标值：", x_train, y_train)
print("测试集特征值和目标值：", x_test, y_test)

lgb_train = lgb.Dataset(x_train, y_train)
lgb_eval = lgb.Dataset(x_test, y_test, reference=lgb_train)

# specify your configurations as a dict
params = {
    'task': 'train',
    'boosting_type': 'gbdt',
    'objective': 'binary',
    'metric': {'binary_logloss'},
    'num_leaves': 63,
    'num_trees': 100,
    'learning_rate': 0.01,
    'feature_fraction': 0.9,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'verbose': 0
}

# number of leaves,will be used in feature transformation
num_leaf = 63

print('Start training...')
# train
gbm = lgb.train(params,
                lgb_train,
                num_boost_round=100,
                valid_sets=lgb_train)

print('Save model...')
# save model to file
gbm.save_model('model.txt')

print('Start predicting...')
# predict and get data on leaves, training data
# y_pred分别落在100棵树上的哪个节点上
y_pred = gbm.predict(x_train, pred_leaf=True)

# feature transformation and write result
print('Writing transformed training data')

# 100棵树，每棵树63个叶子，将其二值化为6300个单位，模型预测的叶子结点的序号为1，其他叶子序号为0
transformed_training_matrix = np.zeros([len(y_pred), len(y_pred[0]) * num_leaf], dtype=np.int64)  # shape (N, (num_tress * num_leafs) )
for i in range(0, len(y_pred)):
    # temp表示在每棵树上预测的值所在节点的序号（0,63,126,...,6237) 为100棵树的序号，它们之间的值为对应树的节点序号）
    temp = np.arange(len(y_pred[0])) * num_leaf + np.array(y_pred[i])
    # 构造one-hot 训练数据集
    transformed_training_matrix[i][temp] += 1

# for i in range(0,len(y_pred)):
#	for j in range(0,len(y_pred[i])):
#		transformed_training_matrix[i][j * num_leaf + y_pred[i][j]-1] = 1

# predict and get data on leaves, testing data
y_pred = gbm.predict(x_test, pred_leaf=True)

# feature transformation and write result
print('Writing transformed testing data')
transformed_testing_matrix = np.zeros([len(y_pred), len(y_pred[0]) * num_leaf], dtype=np.int64)
for i in range(0, len(y_pred)):
    temp = np.arange(len(y_pred[0])) * num_leaf - 1 + np.array(y_pred[i])
    transformed_testing_matrix[i][temp] += 1

# for i in range(0,len(y_pred)):
#	for j in range(0,len(y_pred[i])):
#		transformed_testing_matrix[i][j * num_leaf + y_pred[i][j]-1] = 1

print('Calculate feature importances...')
# feature importances
print('Feature importances:', list(gbm.feature_importance()))
print('Feature importances:', list(gbm.feature_importance("gain")))

# Logestic Regression Start
print("Logestic Regression Start")

# load or create your dataset
print('Load data...')

c = np.array([1, 0.5, 0.1, 0.05, 0.01, 0.005, 0.001])
for t in range(0, len(c)):
    lm = LogisticRegression(penalty='l2', C=c[t])  # logestic model construction
    lm.fit(transformed_training_matrix, y_train)  # fitting the data

    # y_pred_label = lm.predict(transformed_training_matrix )  # For training data
    # y_pred_label = lm.predict(transformed_testing_matrix)    # For testing data
    # y_pred_est = lm.predict_proba(transformed_training_matrix)   # Give the probabilty on each label
    y_pred_est = lm.predict_proba(transformed_testing_matrix)  # Give the probabilty on each label

    # print('number of testing data is ' + str(len(y_pred_label)))
    # print(y_pred_est)

    # calculate predict accuracy
    # num = 0
    # for i in range(0,len(y_pred_label)):
    # if y_test[i] == y_pred_label[i]:
    #	if y_train[i] == y_pred_label[i]:
    #		num += 1
    # print('penalty parameter is '+ str(c[t]))
    # print("prediction accuracy is " + str((num)/len(y_pred_label)))

    # Calculate the Normalized Cross-Entropy
    # for testing data
    NE = (-1) / len(y_pred_est) * sum(
        ((1 + y_test) / 2 * np.log(y_pred_est[:, 1]) + (1 - y_test) / 2 * np.log(1 - y_pred_est[:, 1])))
    # for training data
    # NE = (-1) / len(y_pred_est) * sum(((1+y_train)/2 * np.log(y_pred_est[:,1]) +  (1-y_train)/2 * np.log(1 - y_pred_est[:,1])))
    print("Normalized Cross Entropy " + str(NE))
