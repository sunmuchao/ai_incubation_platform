package base.third.wechat;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;

import java.io.File;
import java.util.HashMap;
import java.util.Map;

public class WechatMessageUtils {

    static final String UPLOAD_FILE_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media";
    static final String SEND_MESSAGE_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send";

    public WechatMessageUtils() {
    }

    /**
     * 企微发消息*
     * @param message 发的消息
     * @param webhook key
     */
    public static void sendMessageToWeChat(String message,String webhook, String user){
        String sendUrl = SEND_MESSAGE_URL + "?key=" + webhook;
        Map<String,Object> msgMap = new HashMap<>();
        msgMap.put("msgtype","text");
        Map<String, String> text = new HashMap<>();
        text.put("content",message);
        msgMap.put("text",text);
        String[] users = new String[] {user};
        msgMap.put("mentioned_list",users);
        cn.hutool.http.HttpUtil.post(sendUrl, JSON.toJSONString(msgMap));
    }

    /**
     * 企微发文件*
     * @param file 文件
     */
    public static void sendFileToWeChat(File file,String key) {
        String url = UPLOAD_FILE_URL + "?key=" + key + "&type=file";
        HashMap<String, Object> sendMap = new HashMap<>();
        sendMap.put("file", file);
        String result = cn.hutool.http.HttpUtil.post(url, sendMap);
        JSONObject jsonObject = JSON.parseObject(result);
        Integer errCode = Integer.valueOf(jsonObject.get("errcode").toString());
        System.out.println(errCode);
        if ("0".equals(String.valueOf(errCode))) {
            String mediaId = (String) jsonObject.get("media_id");
            String sendUrl = SEND_MESSAGE_URL + "?key=" + key;
            Map<String, Object> mediaMap = new HashMap<>();
            mediaMap.put("media_id", mediaId);
            Map<String, Object> msgMap = new HashMap<>();
            msgMap.put("msgtype", "file");
            msgMap.put("file", mediaMap);
            cn.hutool.http.HttpUtil.post(sendUrl, JSON.toJSONString(msgMap));
        } else {
            System.out.println("出错了");
        }
    }

}
