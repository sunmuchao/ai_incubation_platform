package ci.benchMark;// Copyright (c) 2021 Beijing Dingshi Zongheng Technology Co., Ltd. All rights reserved.
//
// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

import org.apache.commons.codec.binary.Base64;
import org.apache.http.HttpHeaders;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpPut;
import org.apache.http.entity.ByteArrayEntity;
import org.apache.http.entity.ContentType;
import org.apache.http.entity.FileEntity;
import org.apache.http.entity.InputStreamEntity;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.DefaultRedirectStrategy;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.util.EntityUtils;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;
import com.mysql.cj.jdbc.Driver;

/**
 * This class is a java demo for starrocks stream load
 * <p>
 * The pom.xml dependency:
 *
 * <dependency>
 * <groupId>org.apache.httpcomponents</groupId>
 * <artifactId>httpclient</artifactId>
 * <version>4.5.3</version>
 * </dependency>
 * <p>
 * How to use:
 * <p>
 * 1 create a table in starrocks with any mysql client
 * <p>
 * CREATE TABLE `stream_test` (
 * `id` bigint(20) COMMENT "",
 * `id2` bigint(20) COMMENT "",
 * `username` varchar(32) COMMENT ""
 * ) ENGINE=OLAP
 * DUPLICATE KEY(`id`)
 * DISTRIBUTED BY HASH(`id`) BUCKETS 20;
 * <p>
 * <p>
 * 2 change the StarRocks cluster, db, user config in this class
 * <p>
 * 3 run this class, you should see the following output:
 * <p>
 * {
 * "TxnId": 27,
 * "Label": "39c25a5c-7000-496e-a98e-348a264c81de",
 * "Status": "Success",
 * "Message": "OK",
 * "NumberTotalRows": 10,
 * "NumberLoadedRows": 10,
 * "NumberFilteredRows": 0,
 * "NumberUnselectedRows": 0,
 * "LoadBytes": 50,
 * "LoadTimeMs": 151
 * }
 * <p>
 * Attention:
 * <p>
 * 1 wrong dependency version(such as 4.4) of httpclient may cause shaded.org.apache.http.ProtocolException
 * Caused by: shaded.org.apache.http.ProtocolException: Content-Length header already present
 * at shaded.org.apache.http.protocol.RequestContent.process(RequestContent.java:96)
 * at shaded.org.apache.http.protocol.ImmutableHttpProcessor.process(ImmutableHttpProcessor.java:132)
 * at shaded.org.apache.http.impl.execchain.ProtocolExec.execute(ProtocolExec.java:182)
 * at shaded.org.apache.http.impl.execchain.RetryExec.execute(RetryExec.java:88)
 * at shaded.org.apache.http.impl.execchain.RedirectExec.execute(RedirectExec.java:110)
 * at shaded.org.apache.http.impl.client.InternalHttpClient.doExecute(InternalHttpClient.java:184)
 * <p>
 * 2 run this class more than once, the status code for http response is still ok, and you will see
 * the following output:
 * <p>
 * {
 * "TxnId": -1,
 * "Label": "39c25a5c-7000-496e-a98e-348a264c81de",
 * "Status": "Label Already Exists",
 * "ExistingJobStatus": "FINISHED",
 * "Message": "Label [39c25a5c-7000-496e-a98e-348a264c81de"] has already been used.",
 * "NumberTotalRows": 0,
 * "NumberLoadedRows": 0,
 * "NumberFilteredRows": 0,
 * "NumberUnselectedRows": 0,
 * "LoadBytes": 0,
 * "LoadTimeMs": 0
 * }
 * 3 when the response statusCode is 200, that doesn't mean your stream load is ok, there may be still
 * some stream problem unless you see the output with 'ok' message
 */
public class StarRocksStreamLoad {
    //    private final static String STARROCKS_HOST = "xxx.com";
//    private final static String STARROCKS_DB = "test";
//    private final static String STARROCKS_TABLE = "stream_test";
//    private final static String STARROCKS_USER = "root";
//    private final static String STARROCKS_PASSWORD = "xxx";
//    private final static int STARROCKS_HTTP_PORT = 8030;
    private final static String STARROCKS_HOST = System.getProperty("host"); //"192.168.101.101";
    private final static String STARROCKS_DB = System.getProperty("db"); //"load_test";
    private final static String STARROCKS_TABLE = System.getProperty("table"); //"load_test_7000";
    private final static String STARROCKS_USER = System.getProperty("user"); //"root";
    private final static String STARROCKS_PASSWORD = System.getProperty("password"); //password
    private final static int STARROCKS_HTTP_PORT = Integer.parseInt(System.getProperty("http_port")); //18030;
    private final static int STARROCKS_MYSQL_PORT = Integer.parseInt(System.getProperty("mysql_port"));
    private final static String csvPath = System.getProperty("csvPath");
    static final String JDBC_DRIVER = "com.mysql.cj.jdbc.Driver";

    private void sendData(String content, String csvPath) throws Exception {
        final String loadUrl = String.format("http://%s:%s/api/%s/%s/_stream_load",
                STARROCKS_HOST,
                STARROCKS_HTTP_PORT,
                STARROCKS_DB,
                STARROCKS_TABLE);

        final HttpClientBuilder httpClientBuilder = HttpClients
                .custom()
                .setRedirectStrategy(new DefaultRedirectStrategy() {
                    @Override
                    protected boolean isRedirectable(String method) {
                        return true;
                    }
                });

        try (CloseableHttpClient client = httpClientBuilder.build()) {
            /*HttpPut put = new HttpPut(loadUrl);
            StringEntity entity = new StringEntity(content, "UTF-8");
            put.setHeader(HttpHeaders.EXPECT, "100-continue");
            put.setHeader(HttpHeaders.AUTHORIZATION, basicAuthHeader(STARROCKS_USER, STARROCKS_PASSWORD));
            // the label header is optional, not necessary
            // use label header can ensure at most once semantics
            put.setHeader("label", "39c25a5c-7000-496e-a98e-348a264c81de");
            put.setEntity(entity);*/
/*
            curl --location-trusted -u root: -H "label:121" \
            -H "column_separator:," \
            -H "columns: date, time, orderID, shopName, shopSite, productName, saleNum, price, cost,profit" \
            -T /data/test/load_test/1000million/load_test_1000million_1.csv -XPUT \
            http://192.168.101.101:18030/api/load_test/load_test_1000million/_stream_load*/

            long time = System.currentTimeMillis() / 1000;

            HttpPut put = new HttpPut(loadUrl);
            //byte[] fileContent = readFileToByteArray(csvPath);
            //ByteArrayEntity entity = new ByteArrayEntity(fileContent);
            FileEntity entity = new FileEntity(new File(csvPath), ContentType.DEFAULT_BINARY);
            //InputStreamEntity entity = new InputStreamEntity(new FileInputStream(csvPath), -1L);

            put.setHeader(HttpHeaders.EXPECT, "100-continue");
            put.setHeader(HttpHeaders.AUTHORIZATION, basicAuthHeader(STARROCKS_USER, STARROCKS_PASSWORD));
            // the label header is optional, not necessary
            // use label header can ensure at most once semantics

            put.setHeader("label", STARROCKS_TABLE + time);
            put.setHeader("column_separator", ",");
            put.setHeader("enclose","\"");
            put.setEntity(entity);

            try (CloseableHttpResponse response = client.execute(put)) {
                String loadResult = "";
                if (response.getEntity() != null) {
                    loadResult = EntityUtils.toString(response.getEntity());
                }
                final int statusCode = response.getStatusLine().getStatusCode();
                // statusCode 200 just indicates that starrocks be service is ok, not stream load
                // you should see the output content to find whether stream load is success
                if (statusCode != 200) {
                    throw new IOException(
                            String.format("Stream load failed, statusCode=%s load result=%s", statusCode, loadResult));
                }

                System.out.println(loadResult);
            }
        }
    }

    private String basicAuthHeader(String username, String password) {
        final String tobeEncode = username + ":" + password;
        byte[] encoded = Base64.encodeBase64(tobeEncode.getBytes(StandardCharsets.UTF_8));
        return "Basic " + new String(encoded);
    }


    private boolean clearTable() throws SQLException {
        String DB_URL = "jdbc:mysql://" + STARROCKS_HOST + ":" + STARROCKS_MYSQL_PORT + "/" + STARROCKS_DB + "?useSSL=false&serverTimezone=UTC";

        Connection conn = null;
        Statement stmt = null;
        try {
            // 注册JDBC驱动。
            Class.forName(JDBC_DRIVER);
            conn = DriverManager.getConnection(DB_URL, STARROCKS_USER, STARROCKS_PASSWORD);
            stmt = conn.createStatement();
            String sql;
            sql = "TRUNCATE TABLE " + STARROCKS_TABLE;
            System.out.println("sql:" + sql);
            //获取查询结果集。
            stmt.executeUpdate(sql);
            System.out.println("Table cleared successfully.");
            return true;
        } catch (SQLException se) {
            // 处理JDBC错误。
            se.printStackTrace();
        } catch (Exception e) {
            // 处理Class.forName错误。m
            return false;
        } finally {
            // 关闭资源。
            if (stmt != null) {
                stmt.close();
            }
            if (conn != null) {
                conn.close();
            }
        }
        return false;
    }

    private byte[] readFileToByteArray(String filePath) throws IOException {
        try (FileInputStream fis = new FileInputStream(new File(filePath));
            ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[1024];
            int bytesRead;
            while ((bytesRead = fis.read(buffer)) != -1) {
                baos.write(buffer, 0, bytesRead);
            }
            return baos.toByteArray();
        }
    }

    public static void main(String[] args) throws Exception {
        int id1 = 1;
        int id2 = 10;
        String id3 = "Simon";
        int rowNumber = 10;
        String oneRow = id1 + "\t" + id2 + "\t" + id3 + "\n";
        Boolean isAppend = Boolean.valueOf(System.getProperty("isAppend"));

        StringBuilder stringBuilder = new StringBuilder();
        for (int i = 0; i < rowNumber; i++) {
            stringBuilder.append(oneRow);
        }

        stringBuilder.deleteCharAt(stringBuilder.length() - 1);

        String loadData = stringBuilder.toString();
        StarRocksStreamLoad starrocksStreamLoad = new StarRocksStreamLoad();
        if(isAppend) {
            starrocksStreamLoad.sendData(loadData, csvPath);
        }else {
            if (starrocksStreamLoad.clearTable()) {
                starrocksStreamLoad.sendData(loadData, csvPath);
            } else {
                System.err.println("Table clearing failed, aborting data load.");
            }
        }
    }
}