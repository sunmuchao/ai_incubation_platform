package ci.benchMark;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.List;

/**
 * @author sunmuchao
 * @date 2024/6/20 4:22 下午
 */
public class Test1 {
    public static void main(String[] args) throws JsonProcessingException {
        String plsValue = "1.2";
        String plsPrefix = plsValue.split("\\.")[0];
        System.out.println(plsPrefix);
    }

}
