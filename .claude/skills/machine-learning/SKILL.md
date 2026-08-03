# Machine Learning Skill

Trigger: any work inside `ml_pipeline/`, or any discussion of model choice,
preprocessing, training, or evaluation.

Act as a senior ML engineer. Always follow this order, and don't skip steps:

1. Data understanding (shape, dtypes, missingness, class balance, target
   definition) before any modelling
2. Cleaning (justify every imputation/removal decision)
3. Feature engineering (check multicollinearity via VIF; document why each
   engineered feature should plausibly relate to stress)
4. Baseline model first (Logistic Regression) before anything fancier —
   without a baseline, "92% accuracy" from XGBoost means nothing
5. Comparative model training across the candidate set (LR, RF, SVM, XGBoost,
   LightGBM, optional NN) — never train and report only one model
6. Hyperparameter tuning via GridSearchCV/RandomizedSearchCV with k-fold CV
7. Evaluation across accuracy, precision, recall, F1, ROC-AUC, balanced
   accuracy, and confusion matrix — and, where feasible, statistical
   significance testing between top candidates, not just a raw score table

Explicitly check for and report on: data leakage (fit scalers/encoders on
training folds only), class imbalance (state whether SMOTE or class weighting
was needed and why), and whether evaluation was internal-only or included a
held-out/external set.

Always justify model selection academically — reference the trade-off (e.g.
"XGBoost was selected over Random Forest despite near-identical accuracy
because it showed higher recall on the minority high-stress class, which
matters more than overall accuracy for an early-warning system").

Never let backend code import training logic — training only happens here.
