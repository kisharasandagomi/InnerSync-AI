# InnerSync AI — Development Roadmap

## Phase 0: Foundation (this batch of files)
- [x] CLAUDE.md, IMPLEMENTATION_RULES.md
- [x] .claude/skills/* (6 skills)
- [x] .claude/agents/dissertation-review-agent.md
- [x] docs/governance/ (ethical_framework, data_management_plan, model_card)
- [ ] Repo scaffolded in VS Code via Claude Code kickoff prompt
- [ ] conda env (`mainks`) confirmed with all required packages

## Phase 1: Research Foundation
- [x] Literature review (Chapter 2) — 17 sources, DS-framed, dataset identified
- [x] Research gap identified (retracted comparable study; explanation
      accessibility gap; adaptive-recommendation gap)
- [ ] Finalize methodology chapter (CRISP-DM mapping) in docs/research/methodology.md
- [ ] Confirm dataset access (Kaggle "Student Stress Factors" + plan for local
      Google Form validation set)

## Phase 2: Data & ML Pipeline
- [ ] EDA notebook (ml_pipeline/notebooks/01_EDA.ipynb)
- [ ] Preprocessing: missing values, VIF/multicollinearity check, encoding
- [ ] Feature engineering: merge questionnaire + (later) NLP-derived features
- [ ] Baseline model (Logistic Regression)
- [ ] Comparative training: Random Forest, SVM, XGBoost, LightGBM
- [ ] Hyperparameter tuning (GridSearchCV + k-fold CV)
- [ ] Evaluation: accuracy, precision, recall, F1, ROC-AUC, balanced accuracy,
      confusion matrix — documented model-selection justification, not accuracy alone
- [ ] Export winning model + preprocessing pipeline to ml_pipeline/artifacts/

## Phase 3: NLP Behaviour Analysis
- [ ] Text preprocessing for conversational input
- [ ] Sentiment analysis (VADER/TextBlob baseline)
- [ ] Emotion/keyword extraction
- [ ] Embedding generation (Sentence Transformers) if time allows
- [ ] Merge NLP features into the ML feature set; re-evaluate model performance

## Phase 4: Explainable AI Framework
- [ ] SHAP integration on the selected model (TreeSHAP if tree-based)
- [ ] Global explanation (which features matter overall)
- [ ] Local explanation (why this student, this prediction)
- [ ] Human-Centered Explanation Generator (SHAP → supportive language)
- [ ] Faithfulness check: does the plain-language explanation match the SHAP
      values it was derived from (log both, compare)

## Phase 5: Personalization Engine
- [ ] Stress profile generator (qualitative, no raw percentages shown)
- [ ] Recommendation rules mapped to dominant SHAP-identified stressors
- [ ] Engagement tracking (was a recommendation acted on)
- [ ] Adaptive Recovery Framework (change strategy after N ignored recommendations)

## Phase 6: Backend Development
- [ ] FastAPI scaffold, JWT auth (register/login)
- [ ] SQLAlchemy models: User, UserProfile, Questionnaire, Conversation,
      StressPrediction, Recommendation, ProgressLog
- [ ] Alembic migrations
- [ ] Endpoints wired to ml_pipeline artifacts via app/ml (load-and-predict only)
- [ ] Chatbot integration (Gemini/OpenAI API) as data-collection layer

## Phase 7: Frontend Development
- [ ] Auth pages, onboarding profile + questionnaire
- [ ] Chat interface
- [ ] Stress Profile + explanation display (human-readable only)
- [ ] Progress Monitoring Dashboard (trends, not raw model output)

## Phase 8: Evaluation
- [ ] ML: final comparative table + SHAP evidence, written up
- [ ] Usability: System Usability Scale (SUS)
- [ ] Explanation clarity + trust questionnaire
- [ ] Recommendation usefulness feedback

## Phase 9: Dissertation Finalization
- [ ] Results & discussion chapters
- [ ] Limitations (explicit — including dataset provenance limits)
- [ ] Future work
- [ ] dissertation-review-agent pass on every chapter before submission
- [ ] Presentation preparation
