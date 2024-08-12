package ci.benchMark;

import base.db.JSYDBUtils;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.List;

/**
 * @author sunmuchao
 * @date 2024/4/30 3:51 下午
 */
public class test {
    public static void main(String[] args) throws Exception {
        File file = new File("/Users/sunmuchao/Downloads/polars-bcs/rset/uuid-1234.csv");
        PR pr = new PR("feature/3.0","Sun.Sun", "4957");
        String uuid = benchmarkResultMetaDataToDB("java", pr.getPrId());
        csvResultToDB(file, uuid);
    }

    private static String benchmarkResultMetaDataToDB(String codeType, String prid) {
        String uuid = String.valueOf(System.currentTimeMillis());
        String sql = "INSERT INTO benchmarkResultMetaData (codeType, prid, uuid) VALUES (\"" + codeType + "\", \"" + prid + "\", \"" + uuid + "\")";
        JSYDBUtils.updateData(sql);
        return uuid;
    }

    private static void csvResultToDB(File csv, String uuid) throws IOException, SQLException {
        try (Reader reader = new InputStreamReader(new FileInputStream(csv), StandardCharsets.UTF_8);
             CSVParser csvParser = new CSVParser(reader, CSVFormat.DEFAULT.withFirstRecordAsHeader().withQuote('"').withEscape('\\'))) {

            // Prepare the insert statement dynamically based on CSV headers
            StringBuilder insertQuery = new StringBuilder("INSERT INTO benchmarkResult (uuid,");
            StringBuilder valuePlaceholders = new StringBuilder(") VALUES (?,");

            // Get headers from CSV
            List<String> headers = csvParser.getHeaderNames();

            // Append column names and placeholders for values
            for (int i = 0; i < headers.size(); i++) {
                if (i > 0) {
                    insertQuery.append(", ");
                    valuePlaceholders.append(", ");
                }
                insertQuery.append(headers.get(i));
                valuePlaceholders.append("?");
            }

            insertQuery.append(valuePlaceholders).append(")");

            PreparedStatement preparedStatement = JSYDBUtils.getConnection().prepareStatement(insertQuery.toString());

            for (CSVRecord record : csvParser) {
                preparedStatement.setString(1, uuid);
                for (int i = 0; i < headers.size(); i++) {
                    String columnName = headers.get(i);
                    String value = record.get(columnName);

                    preparedStatement.setString(i + 2, value);
                }

                preparedStatement.executeUpdate();
            }
        }
    }
}
