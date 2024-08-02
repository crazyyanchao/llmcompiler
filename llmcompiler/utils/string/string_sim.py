# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""


def jaccard_sim_ngram(answer, ref, ngram=2):
    if answer in ref: return 1.0
    if len(answer) - ngram > 0:
        answer_ngrams = [answer[i: i + ngram] for i in range(0, len(answer) - ngram + 1)]
    else:
        answer_ngrams = answer  # 退化到unigram
    if len(ref) - ngram > 0:
        ref_ngrams = [ref[i: i + ngram] for i in range(0, len(ref) - ngram + 1)]
    else:
        ref_ngrams = ref  # 退化到unigram
    intersection = len(set(answer_ngrams).intersection(set(ref_ngrams)))
    # union = len(set(answer).union(set(ref)))
    return float(intersection) / len(set(ref_ngrams))


def word_similarity_score(word1, word2):
    m, n = len(word1), len(word2)
    # 创建一个(m+1) x (n+1)的二维数组来存储Levenshtein距离
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    # 初始化第一行和第一列
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    # 计算Levenshtein距离
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if word1[i - 1] == word2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[m][n]


if __name__ == '__main__':
    print(word_similarity_score('date', 'datec'))
