
package buriedPoint;

import java.io.*;
import java.util.*;

import base.http.HttpUtils;
import buriedPoint.executor.DataFlowExecutor;
import buriedPoint.executor.Executor;
import buriedPoint.executor.QueryExecutor;
import buriedPoint.point.BuriedPoint;
import buriedPoint.processor.BPProcessor;
import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import base.config.Application;

public class BuriedPointTool {
    public static void polarsTimeOut(ArrayList<String> data) throws Exception {
        DBUtils dbUtils = Application.getDBUtilsInstance();
        BuriedPoint buriedPoint = null;
        outloopA:
        for (int i = 0; i < data.size(); i++) {
            String traceid = data.get(i);
            System.out.println("traceid=" + traceid);
            String url = "https://work.jiushuyun.com/decision/zipkin/api/v2/trace/" + traceid;
            HttpUtils httpUtils = new HttpUtils(url, Application.jsyCookie);
            String response = httpUtils.connectAndGetRequest();
            JSONArray jsonArray = JSON.parseArray(response);
            if (jsonArray != null && jsonArray.toString().equals("[]")) {
                //dbUtils.resIntoDB(traceid, "zipkin数据丢失", 0, "jsy");
                continue outloopA;
            } else if (httpUtils.getResponseCode() != 0 && httpUtils.getResponseCode() == 503) {
                i--;
                continue outloopA;
            }
            //创建buriedPint对象
            for (int x = 0; x < jsonArray.size(); x++) {
                JSONObject jsonObject = jsonArray.getJSONObject(x);
                if (jsonObject.getString("kind") != null && jsonObject.getString("kind").equals("SERVER")
                    && (jsonObject.getString("name").equals("homepreview") || jsonObject.getString("name").equals("homepreview")
                    || jsonObject.getString("name").equals("operatorspage")
                    || jsonObject.getString("name").equals("editchart") || jsonObject.getString("name").equals("widgetdata")
                    || jsonObject.getString("name").equals("linkagerows") || jsonObject.getString("name").equals("previewchart")
                    || jsonObject.getString("name").equals("filter.getstringvalues") || jsonObject.getString("name").equals("join.stepDetail")
                )) {
                    BuriedPointFactory buriedPointFactory = new BuriedPointFactory();

                    buriedPoint = buriedPointFactory.createBuriedPoint(jsonObject.getString("name"),traceid);

                    //先跳过图表:缺少表名
                    if(buriedPoint.getClass().getName().contains("EditChartBuriedPoint")){
                        continue outloopA;
                    }

                    JSONObject tags = JSON.parseObject(jsonObject.getString("tags"));
                    buriedPoint.setOperatorType(tags.getString("operatorType"));
                    buriedPoint.setSense(tags.getString("sense"));
                    buriedPoint.setUserName(tags.getString("userName"));

                    buriedPoint.setWidgetName(jsonObject.getString("widgetName"));

                    buriedPoint.setStartTime(jsonObject.getString("timestamp"));
                    buriedPoint.setTotalTime(jsonObject.getString("duration"));
                    break;
                }else if(jsonObject.getString("name") != null && jsonObject.getString("name").equals("update") ){

                    BuriedPointFactory buriedPointFactory = new BuriedPointFactory();
                    buriedPoint = buriedPointFactory.createBuriedPoint(jsonObject.getString("name"),traceid);
                    JSONObject tags = JSON.parseObject(jsonObject.getString("tags"));
                    buriedPoint.setTableName(tags.getString("tableName"));
                    buriedPoint.setUserName(tags.getString("userName"));

                    buriedPoint.setUpdateStartTime(jsonObject.getString("timestamp"));
                    buriedPoint.setTotalTime(jsonObject.getString("duration"));
                    break;
                }

                //不包含SERVER部分
                if(x == jsonArray.size() - 1){
                    dbUtils.resIntoDB(traceid, "zipkin数据丢失", 0, "jsy");
                    continue outloopA;
                }
            }

            initQueryExecutor(jsonArray, buriedPoint);

            for (int x = 0; x < jsonArray.size(); x++) {
                JSONObject jsonObject = jsonArray.getJSONObject(x);
                if (jsonObject.getString("name") != null && jsonObject.getString("name").equals("execute")) {
                    String id = jsonObject.getString("id");
                    if(buriedPoint.getClass().getName().contains("UpdateBuriedPoint")){
                        JSONObject tags = jsonObject.getJSONObject("tags");
                        for(Executor executor : buriedPoint.Executors){
                            if(executor.getClass().getName().contains("DataFlowExecutor")){
                                for(String child : executor.childIds){
                                    if(child.equals(id)){
                                        executor.setMetric(tags.getString("metric"));
                                        executor.setPls(tags.getString("pls"));
                                        executor.setSuite(tags.getString("suite"));
                                    }
                                }
                            }
                        }
                    }

                } else if (jsonObject.getString("name") != null && jsonObject.getString("name").equals("fetchblock")) {
                    for(Executor qe : buriedPoint.Executors){
                        for(String childId : qe.childIds){
                            if(childId.equals(jsonObject.getString("parentId"))){
                                ((QueryExecutor) qe).addFetchblockTime(jsonObject.getInteger("duration"));
                            }
                        }
                    }

                } else if (jsonObject.getString("name") != null && jsonObject.getString("name").equals("ensuretablespace")) {
                    buriedPoint.addEnsuretablespacetime(jsonObject.getInteger("duration"));

                } else if(jsonObject.getString("name") != null && jsonObject.getString("name").equals("queue")){
                    for(Executor qe : buriedPoint.Executors){
                        for(String childId : qe.childIds){
                            if(childId.equals(jsonObject.getString("id"))){
                               qe.setQueueTime(jsonObject.getInteger("duration"));
                            }
                        }
                    }
                }

                if (jsonObject.getString("localEndpoint") != null) {
                    JSONObject localEndpointObject = JSON.parseObject(jsonObject.getString("localEndpoint"));
                    if(localEndpointObject.getString("serviceName") != null
                            && localEndpointObject.getString("serviceName").equals("polars")){
                        buriedPoint.setTotoalPolarsTime(jsonObject.getInteger("duration"));
                    }
                    if(buriedPoint.getJsyaddr() != null) {
                        buriedPoint.setJsyaddr(localEndpointObject.getString("ipv4"));
                    }
                }
                if (jsonObject.getString("tags") != null) {
                    JSONObject tags = JSON.parseObject(jsonObject.getString("tags"));
                    buriedPoint.setTableId(tags.getString("tableId"));
                    buriedPoint.setTableName(tags.getString("tableName"));
                }
            }

            BPProcessorFactory bpProcessorFactory = new BPProcessorFactory(buriedPoint,dbUtils,traceid, Application.jsyCookie);
            BPProcessor bpProcessor = bpProcessorFactory.createProcessor();
            bpProcessor.process();
        }
    }


    private static void initQueryExecutor(JSONArray jsonArray,BuriedPoint buriedPoint) {
        //先初始化:维护节点关系和初始化所有QueryExecutor节点
        for (int x = 0; x < jsonArray.size(); x++) {
            JSONObject jsonObject = jsonArray.getJSONObject(x);
            if(jsonObject.getString("name") != null && jsonObject.getString("name").equals("queryexecutor")){
                Executor queryExecutor = new QueryExecutor(jsonObject.getString("id"), jsonObject.getInteger("duration"));
                buriedPoint.addExecutor(queryExecutor);
                JSONObject tags = JSON.parseObject(jsonObject.getString("tags"));
                queryExecutor.setMetric(tags.getString("metric"));
                queryExecutor.setSuite(tags.getString("suite"));
                queryExecutor.setPls(tags.getString("pls"));
            } else if(jsonObject.getString("name") != null && jsonObject.getString("name").equals("dataflowexecutor")){
                Executor dataFlowExecutor = new DataFlowExecutor(jsonObject.getString("id"), jsonObject.getInteger("duration"));
                buriedPoint.addExecutor(dataFlowExecutor);
            }
        }

        for (int x = 0; x < jsonArray.size(); x++) {
            JSONObject jsonObject = jsonArray.getJSONObject(x);
            if(jsonObject.getString("name") != null){
                String id = jsonObject.getString("id");
                String parentId = jsonObject.getString("parentId");
                for(Executor qe : buriedPoint.Executors){
                    if(qe.getClass().getName().contains("QueryExecutor")) {
                        if (((QueryExecutor) qe).getQueryExecutorId().equals(parentId)) {
                            qe.addChildId(id);
                        }
                    }else if(qe.getClass().getName().contains("DataFlowExecutor")){
                        if (((DataFlowExecutor) qe).getDataFlowExecutorId().equals(parentId)) {
                            qe.addChildId(id);
                        }
                    }
                }
            }
        }
    }

    public static void main(String[] args) {
        try {
            //Application.setJsyCookie("fine_remember_login=-1; fr_id_appname=jiushuyun; last-serviceName=hihidata; tenantId=d7c9badb990c427ea6303af0ce2125f8; fine_auth_token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJiNGExMjQwNjM5MGY0ZmI1OWQyNTFkMDc2YTZkN2ZiYiIsInRlbmFudElkIjoiZDdjOWJhZGI5OTBjNDI3ZWE2MzAzYWYwY2UyMTI1ZjgiLCJpc3MiOiJmYW5ydWFuIiwiZGVzY3JpcHRpb24iOiJbNzUyOF1bNjIzN11yRk1TTTY4MTExOTMoYjRhMTI0MDYzOTBmNGZiNTlkMjUxZDA3NmE2ZDdmYmIpIiwiZXhwIjoxNjcwMTE3NDUyLCJpYXQiOjE2Njk4NTgyNTIsImp0aSI6IkF0ODdRY0RtREJYZ0JySjJ6eUgvUVNoT1JEZlNtNkl0WlB2cDRHVWYzZVNkTEU1WSJ9.lP3pIqJCXDU8geLJUPfxyuYGx0aY8GwAAf7OYJWyToc; fr_id_auth=7DBF1DB5CF3EB26298E4DB072ADF5FFC5738D868CB4E2E387A72438216948EB7CB0B5C10123D6D0CF9E30594E333F543631CD98824BF0DE92A477822763C0E2A3132B402A22DA62ABFC16D6F3EECA7A731FB161FD123DB26F615AB32020B055D0240D44C16027E9E127BEE118BD93A6F55C59CFAE230BFC8B3983B5CAD82CBD8C9E6913A78D52927F2BEFD8A99AB1D0D6822F7BE37B33F0275ADB8A8EB9B70104E0D9BFAFFB8D0CFDA40C1A80453EAC26DA1FF79F7E96CB701D147F120CEE8F91EBAE117647CA27F2CFB3011DD6A90B44D2B14084A10AFD3A3C28374AB341981C141DFBFD4B29C91F347633CAFE83EB8E0D1B8BB65530F2ED09023EF86C36302019441B682DD27BB229C89F84FB307A1E0E3105E35454F03210A9272766D0B315B5A9A3E5920EE950340EA633A7D010DBB49DBE8C5F5C08C04A66203CA5FD29320DAB2F44CCA0F635FFA1207632654A3D60580F37ACFC9708E50E26DBD3498C6768FA06C27A4CD84DC3B09DE4E7E30F3503F5019A6B4ED28F8693D9B0E3ED0D7DD1DCF8249B3E46A2C11ED542A326E2635BB608E91571D0BE40B4BCA30CDD6BCE88ACB140442404620D15D13DE22F1BCED6EE22F209AB952BA58FBE3F7A5CAA6DCAC72BB37F5AC9D53816F9ADF804C25B528028CC3C7627A6D3962D175842D685F305EA8FCDD3E987569EFE5F2A907CCDB8C09E73926C961C5E616BC01F2040C2442BC27395C7B9BE4302DC29C6D2F76AEF188AAF55B42CF204B627AA3CEEDE5BC525C455D049B7CEF8171B8A342582A281B9F838417D311B02A0DF511EC082C765BD020F2A40AA57AC39A09E732542DA8C2021EC97B8CC3810B97BAC1C13B66B0D8BEFD30860A022097F34ACAA424D9DC562985D5488502DAD5225B4AF7576488F194175F9B413CA3D94F3D");
            Application.setJsyCookie(args[1]);
            //末尾加/
            Application.setWorkPath(args[0]);
            //Application.setWorkPath("/Users/sunmuchao/Downloads/smc/");
            ArrayList data = new ArrayList<String>();
            File file = new File(Application.workPath + "埋点数据");
            String line = null;
            BufferedReader reader = new BufferedReader(new FileReader(file));
            while ((line = reader.readLine()) != null) {
                data.add(line);
            }
            polarsTimeOut(data);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}