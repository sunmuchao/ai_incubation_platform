package base.file;

import com.jcraft.jsch.Channel;
import com.jcraft.jsch.*;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.InputStream;

public class RemoteFileUtils extends FileUtils {
    private String ip;
    private int port;
    private String user;
    private String password;
    private String path;
    private ChannelSftp sftp;

    public RemoteFileUtils(String ip, int port, String user, String password, String path) throws Exception {
        this.ip = ip;
        this.port = port;
        this.user = user;
        this.password = password;
        this.path = path;
        sshSftp();
    }

    /**
     * 利用JSch包实现SFTP上传文件
     *
     * @param bytes    文件字节流
     * @param fileName 文件名
     * @throws Exception
     */
    public void sshSftp() throws Exception {
        Session session = null;
        Channel channel = null;

        JSch jsch = new JSch();

        if (port <= 0) {
            //连接服务器，采用默认端口
            session = jsch.getSession(user, ip);
        } else {
            //采用指定的端口连接服务器
            session = jsch.getSession(user, ip, port);
        }

        //如果服务器连接不上，则抛出异常
        if (session == null) {
            throw new Exception("session is null");
        }

        //设置登陆主机的密码
        session.setPassword(password);//设置密码
        //设置第一次登陆的时候提示，可选值：(ask | yes | no)
        session.setConfig("StrictHostKeyChecking", "no");
        //设置登陆超时时间
        session.connect(30000);
        try {
            //创建sftp通信通道
            channel = (Channel) session.openChannel("sftp");
            channel.connect(1000);
            sftp = (ChannelSftp) channel;

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public boolean isExistDirectly(String directory)  {
        try {
            sftp.cd(path + "/" + directory);
            return true;
        } catch (SftpException e) {
            return false;
        }
    }


    public void upload(String directory, File uploadFile) throws FileNotFoundException, SftpException {
        if (directory != null) {
            directory = path + "/" + directory;
        } else {
            return;
        }
        upload(directory, uploadFile.getName(), new FileInputStream(uploadFile));
    }

    public void upload(String directory, String sftpFileName, InputStream input) throws SftpException {
        try {
            sftp.cd(directory);
        } catch (SftpException e) {
            sftp.mkdir(directory);
            sftp.cd(directory);
        }
        sftp.put(input, sftpFileName);
    }
}