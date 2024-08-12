package base.http;

import com.jcraft.jsch.*;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class JSchUtil  {

    public JSchUtil(){
    }

    private Session session = null;

    public Session initializeSession(String userName,String host,String passWord) throws JSchException {
        JSch jSch = new JSch();
        session = jSch.getSession(userName,host);
        session.setPassword(passWord);
        session.setConfig("StrictHostKeyChecking", "no");
        session.setTimeout(10000);
        session.connect(10000);
        return session;
    }

    public Session getSession(){
        return session;
    }

    public void closeSession(){
        session.disconnect();
    }

    /**
     * 底层方法，执行linux命令
     * @param command linux命令
     * @return 返回结果为String形式
     */
    public String execQuery(String command){
        ChannelExec channelExec = null;
        StringBuilder sb = new StringBuilder();
        try{
            channelExec = (ChannelExec) session.openChannel("exec");
            System.out.println(command);
            channelExec.setCommand(command);
            channelExec.setErrStream(System.err);
            channelExec.setInputStream(null);
            channelExec.connect();

            InputStream inputStream = channelExec.getInputStream();
            InputStreamReader inputStreamReader = new InputStreamReader(inputStream, StandardCharsets.UTF_8);
            BufferedReader reader = new BufferedReader(inputStreamReader);
            String buffer;
            while ((buffer = reader.readLine())!=null){
                sb.append("\r\n").append(buffer);
 //               System.out.println(buffer);
            }
            channelExec.disconnect();
            System.out.println("执行命令结束!");
            return sb.toString();

        } catch (JSchException | IOException e) {
            e.printStackTrace();
        } finally {
            if(channelExec != null && !(channelExec.isClosed())){
                channelExec.disconnect();
            }
        }
        return sb.toString();
    }

    /**
     * 底层方法，执行linux命令
     * @param command linux命令
     * @return 返回结果为list形式，按照行划分
     */
    public List<String> execQueryList(String command){
        ChannelExec channelExec = null;
        List<String> list = new ArrayList<>();
        try{
            channelExec = getChannelExec(command);

            InputStream inputStream = channelExec.getInputStream();
            InputStreamReader inputStreamReader = new InputStreamReader(inputStream, StandardCharsets.UTF_8);
            BufferedReader reader = new BufferedReader(inputStreamReader);
            String buffer;
            while ((buffer = reader.readLine())!=null){
                list.add(buffer);
//                System.out.println(buffer);
            }
            channelExec.disconnect();
            System.out.println("执行命令结束!");
            return list;

        } catch (JSchException | IOException e) {
            e.printStackTrace();
        } finally {
            if(channelExec != null && !(channelExec.isClosed())){
                channelExec.disconnect();
            }
        }
        return list;
    }


    /**
     * 底层方法，获得linux命令执行的载体
     * @param command linux命令
     * @return 返回载体
     * @throws JSchException 抛出linux执行可能遇到的错误供上层处理
     */
    private ChannelExec getChannelExec(String command) throws JSchException {
        ChannelExec channelExec = (ChannelExec) session.openChannel("exec");
        System.out.println(command);
        channelExec.setCommand(command);
        channelExec.setErrStream(System.err);
        channelExec.setInputStream(null);
        channelExec.connect();
        return channelExec;
    }


}