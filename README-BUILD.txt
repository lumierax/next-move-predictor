Next Move Predictor - iOS unsigned IPA builder

This package is designed to be added to your existing GitHub repository:
https://github.com/lumierax/next-move-predictor

Files to upload while preserving folders:
- project.yml
- NextMovePredictor/NextMovePredictorApp.swift
- NextMovePredictor/ContentView.swift
- .github/workflows/build-ipa.yml

Build steps on GitHub:
1. Upload/commit these files to the repository.
2. Open the repository -> Actions.
3. Choose "Build unsigned IPA".
4. Press "Run workflow".
5. After the job completes, download artifact "NextMovePredictor-unsigned-ipa".
6. Extract it to get NextMovePredictor-unsigned.ipa.
7. Import the IPA into ESign, sign it with your certificate, and install.

The app loads:
https://lumierax.github.io/next-move-predictor/

Because the UI comes from the live website, future website updates appear inside the app without rebuilding the IPA.
