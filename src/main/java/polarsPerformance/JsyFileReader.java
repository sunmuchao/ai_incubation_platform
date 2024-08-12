package polarsPerformance;

import java.io.*;

public class JsyFileReader {
    File file;
    JsyFileReader(File file){
        this.file = file;
    }

    public StringBuffer read() throws IOException {
        StringBuffer res = new StringBuffer();
        BufferedReader reader = null;
        String line;
        try {
            reader = new BufferedReader(new FileReader(file));
            while ((line = reader.readLine())!= null){
                res.append(line + "\n");
            }
        } catch (IOException e) {
            e.printStackTrace();
        }finally {
            if(reader != null) {
                reader.close();
            }
        }
        return res;
    }

    public StringBuffer readAfterCleanUp() throws IOException {
        StringBuffer res = new StringBuffer();
        BufferedReader reader = null;
        String line;
        FileWriter writer = null;
        try {
            reader = new BufferedReader(new FileReader(file));
            while ((line = reader.readLine())!= null){
                res.append(line + "\n");
            }
            writer = new FileWriter(file);
            writer.write("");
        } catch (IOException e) {
            e.printStackTrace();
        }finally {
            if(reader != null) {
                reader.close();
            }
            if(writer != null){
                writer.close();
            }
        }
        return res;
    }
}
