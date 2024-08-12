FROM centos:7
# 替换yum源
#COPY CentOS-Base.repo /etc/yum.repos.d/
# 更新软件
#RUN yum -y upgrade
# 安装中文包
RUN yum install -y kde-l10n-Chinese
RUN yum -y reinstall glibc-common
RUN localedef -c -f UTF-8 -i zh_CN zh_CN.utf8
RUN echo 'LANG="zh_CN.UTF-8"' > /etc/locale.conf
ENV LANG zh_CN.UTF-8
ENV LC_ALL zh_CN.UTF-8
#设置时区
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo "Asia/Shanghai" > /etc/timezone
WORKDIR /usr
RUN mkdir jdk
RUN mkdir maven
ADD jdk11 /usr/jdk/
#ADD jdk1.8.0 /usr/jdk/
ADD apache-maven/ /usr/maven/
RUN mkdir polarstest
RUN mkdir nas
RUN yum -y install vim net-tools
WORKDIR /usr/maven/polarstest
ENV JAVA_HOME=/usr/jdk
ENV JRE_HOME=$JAVA_HOME/jre
ENV CLASSPATH=.:$JAVA_HOME/lib/dt.jar:$JAVA_HOME/lib/tools.jar:$JRE_HOME/lib:$CLASSPATH
ENV PATH=$JAVA_HOME/bin:$PATH
ENV MAVERN_HOME=/usr/maven
ENV PATH=$PATH:$MAVERN_HOME/bin
ADD fdb_clients.rpm /usr/maven/polarstest/
ADD fdb_server.rpm /usr/maven/polarstest/
RUN rpm -ivh fdb_server.rpm && rm fdb_server.rpm
RUN rpm -ivh fdb_clients.rpm  && rm fdb_clients.rpm
CMD ["mvn --version && mvn clean package -Dmaven.test.skip=true && mvn install -Dmaven.test.skip=true","run"]