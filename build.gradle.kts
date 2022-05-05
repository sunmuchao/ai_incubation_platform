plugins {
    java
    maven
}

group = "com.fanruan.opensource"
version = "2.0"
tasks.withType<JavaCompile>().configureEach {
    options.encoding = "UTF-8"
}

repositories {
    mavenCentral()
    maven(url = "https://mvn.fanruan.com/repository/maven-public/")
}

java {
    sourceCompatibility = JavaVersion.VERSION_1_8
    targetCompatibility = JavaVersion.VERSION_1_8
}

tasks {

    "uploadArchives"(Upload::class) {

        repositories {

            withConvention(MavenRepositoryHandlerConvention::class) {

                mavenDeployer {

                    withGroovyBuilder {
                        "repository"("url" to uri("https://mvn.fanruan.com/repository/fanruan-release")) {
                            "authentication"("userName" to System.getProperty("username"), "password" to System.getProperty("password"))
                        }
                        "snapshotRepository"("url" to uri("https://mvn.fanruan.com/repository/fanruan")) {
                            "authentication"("userName" to System.getProperty("username"), "password" to System.getProperty("password"))
                        }
                    }

                    pom.project {
                        withGroovyBuilder {
                            "licenses" {
                                "license" {
                                    "name"("The Apache Software License, Version 2.0")
                                    "url"("http://www.apache.org/licenses/LICENSE-2.0.txt")
                                    "distribution"("repo")
                                }
                            }
                        }
                    }
                    pom.artifactId = "demo"
                }
            }
        }
    }
}
