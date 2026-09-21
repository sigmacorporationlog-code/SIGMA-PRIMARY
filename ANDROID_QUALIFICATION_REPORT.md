# ANDROID QUALIFICATION REPORT

**Status: BLOCKED — ENVIRONMENT NOT AVAILABLE**

Java 21.0.11 est disponible.

Le projet déclare Gradle wrapper 8.9, compileSdk/targetSdk 35 et Java source/target 17.

Mais :
- Android SDK absent ;
- `adb` absent ;
- Gradle standalone absent ;
- aucune distribution Gradle 8.9 en cache ;
- le wrapper tente `https://services.gradle.org/distributions/gradle-8.9-bin.zip` et échoue par résolution DNS.

Le build APK/AAB, l'installation et l'authentification mobile ne sont donc pas certifiés.

Le bit exécutable de `mobile/android/gradlew` a été corrigé dans le workspace de qualification.
