package buriedPoint.executor;

import java.util.ArrayList;

public class QueryExecutor extends Executor{
    private String queryExecutorId;
    private int queryExecutorTime;
    private int fetchblockTime;

    public QueryExecutor(String queryExecutorId, int queryExecutorTime){
        this.queryExecutorId = queryExecutorId;
        this.queryExecutorTime = queryExecutorTime;
        childIds = new ArrayList();
    }

    public int getqueryExecutorTime() {
        return queryExecutorTime;
    }



    public String getQueryExecutorId(){
        return queryExecutorId;
    }



    public int getFetchblockTime() {
        return fetchblockTime;
    }

    public void addFetchblockTime(int fetchblockTime) {
        this.fetchblockTime += fetchblockTime;
    }
}
