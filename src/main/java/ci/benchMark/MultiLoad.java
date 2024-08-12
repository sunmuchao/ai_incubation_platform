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

import com.google.common.util.concurrent.ThreadFactoryBuilder;
import org.apache.commons.codec.binary.Base64;
import org.apache.http.HttpHeaders;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpPut;
import org.apache.http.entity.InputStreamEntity;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.DefaultRedirectStrategy;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.util.EntityUtils;

import java.io.FileInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

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
public class MultiLoad {
    private final static String STARROCKS_HOST = "192.168.101.101";
    private final static String STARROCKS_DB = "sync_query";
    //    private final static String STARROCKS_TABLE = "load_test_7000";
    private final static String STARROCKS_USER = "root";
    private final static String STARROCKS_PASSWORD = "";
    private final static int STARROCKS_HTTP_PORT = 18030;

    public static ExecutorService threadPool;

    public static final AtomicInteger CSV_NUM = new AtomicInteger(0);

    public static long startTime;

    private void startLoad(int fileNum, String tableName, boolean loadIntoOne, String rowNum) throws Exception {

        threadPool = new ThreadPoolExecutor(
                16, 17,
                3L, TimeUnit.SECONDS,
                new LinkedBlockingQueue<>(),
                new ThreadFactoryBuilder().setNameFormat("Thread-for-CsvLoad-%d").build()
        );


        for (int i = 0; i < fileNum; i++) {
            CSV_NUM.getAndAdd(1);
        }

        String prefix = "/data/test/sync_query/source_data/";


        startTime = System.currentTimeMillis();
        System.out.println("start load: " + startTime);
        System.out.println("file rowNum: " + rowNum);
        System.out.println("file nums: " + fileNum);
        if (loadIntoOne) {
            System.out.println("load mode: multiple files Into one table");
        } else {
            System.out.println("load mode: multiple files Into multiple different tables");
        }
        String labelPrefix = String.valueOf(startTime);

//        for (int i = 1; i <= fileNum; i++) {
        for (int i = 1; i <= fileNum; i++) {
            String filePath = prefix + tableName + "_" + i + ".csv";
            String label;
            if (i < 10) {
                label = labelPrefix + "-00" + i;
            } else if (i < 100) {
                label = labelPrefix + "-0" + i;
            } else {
                label = labelPrefix + "-" + i;
            }

            String table;
            if (loadIntoOne) {
                table = tableName;
            } else {
                table = tableName + "_" + i + "a";

            }

            Thread t = new Thread() {
                @Override
                public void run() {
                    try {
//                        sendData(filePath, table, label);
                        sendData(filePath, "sale_1000million_2a", label);
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
            };
            t.setDaemon(true);
            threadPool.execute(t);
        }

    }

    private void sendData(String filePath, String tableName, String label) throws Exception {
        final String loadUrl = String.format("http://%s:%s/api/%s/%s/_stream_load",
                STARROCKS_HOST,
                STARROCKS_HTTP_PORT,
                STARROCKS_DB,
                tableName);

        final HttpClientBuilder httpClientBuilder = HttpClients
                .custom()
                .setRedirectStrategy(new DefaultRedirectStrategy() {
                    @Override
                    protected boolean isRedirectable(String method) {
                        return true;
                    }
                });

        try (CloseableHttpClient client = httpClientBuilder.build()) {

            HttpPut put = new HttpPut(loadUrl);

            InputStreamEntity entity = new InputStreamEntity(new FileInputStream(filePath), -1L);

            put.setHeader(HttpHeaders.EXPECT, "100-continue");
            put.setHeader(HttpHeaders.AUTHORIZATION, basicAuthHeader(STARROCKS_USER, STARROCKS_PASSWORD));
            put.setHeader("label", label);
            put.setHeader("column_separator", ",");
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

                CSV_NUM.getAndAdd(-1);
                if (CSV_NUM.get() == 0) {
                    long endT = System.currentTimeMillis();
                    System.out.println("end load: " + endT);
                    long timeCost = endT - startTime;
                    System.out.println("Time cost: " + timeCost + "ms");
                    System.exit(1);
                } else {
                    System.out.println("still remaining csv files to load: " + CSV_NUM.get());
                }
            }
        }
    }

    private String basicAuthHeader(String username, String password) {
        final String tobeEncode = username + ":" + password;
        byte[] encoded = Base64.encodeBase64(tobeEncode.getBytes(StandardCharsets.UTF_8));
        return "Basic " + new String(encoded);
    }

    public static void main(String[] args) throws Exception {
        MultiLoad load = new MultiLoad();
        //行数：10亿行，文件数：1，单表场景，写入一张表中
//        load.startLoad(1, "load_test_1000million", true, "1000million");

        //行数：1亿行，文件数：10，单表场景，写入一张表中

//        load.startLoad(10, "load_test_100million", true, "100million");
        //行数：2千万行，文件数：50，单表场景，写入一张表中
//        load.startLoad(50, "load_test_20million", true,"20million");

        //行数：1亿行，文件数：10，多表场景，分别写入10张不同的表中
//        load.startLoad(10, "load_test_100million", false, "100million");

        //行数：2千万行，文件数：50，多表场景，分别写入50张不同的表中
//        load.startLoad(50, "load_test_20million", false,"20million");


//        load.startLoad(10, "sale_100million", false,"100million");
//        for(int i=2;i<=10;i++){
//            String name="sale_1000million_"+i+"a";
//            load.startLoad(10, "sale_100million", true, "100million",name);
//
//        }
        load.startLoad(10, "sale_100million", true, "100million");
//        load.startLoad(1, "sale_1000million", false,"1000million");
    }
}