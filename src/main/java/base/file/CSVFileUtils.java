/*
package base.file;

import com.opencsv.CSVReader;

import java.io.IOException;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

public class CSVFileUtils {
    public List<Object> ReadCsvTransformObj(String csvPath, Object obj) throws IOException, IllegalAccessException, InstantiationException {
        //解析csv文件
        List<Object> list = new ArrayList<>();
        CSVReader csvReader = new CSVReader(Files.newBufferedReader(Paths.get(csvPath)));
        String[] fields;
        //映射对象
        while ((fields = csvReader.readNext()) != null) {
            Class clazz = obj.getClass(); // 通过反射获取运行时类
            Object infos = clazz.newInstance(); // 创建运行时类的对象
            Field[] fs = infos.getClass().getDeclaredFields();
            for (int i = 0; i < fs.length; i++) {
                Field f = fs[i];
                f.setAccessible(true); // 设置这些属性值是可以访问的
                if(f.getName().equals(fields[i])){

                }
            }
            list.add(infos);
        }
        return list;
    }
}
*/
