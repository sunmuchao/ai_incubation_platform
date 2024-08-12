package ci.benchMark;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * @author sunmuchao
 * @date 2023/11/17 2:51 下午
 */

//BenchMarkResult负责将结果进行整合
public class BenchMarkResult {
    private List<Map<String, String>> allFails;
    private List<Map<String, String>> allReducedPerfs;
    private List<Map<String, String>> allOverlapRisePerfs;

    BenchMarkResult(){
        this.allFails = new ArrayList<>();
        this.allReducedPerfs = new ArrayList<>();
        this.allOverlapRisePerfs = new ArrayList<>();
    }


    public List<Map<String, String>> getFails() {
        return allFails;
    }

    public void addFails(List<Map<String, String>> fails) {
        allFails.addAll(fails);
    }

    public List<Map<String, String>> getReducedPerfs() {
        return allReducedPerfs;
    }

    public void addReducedPerfs(List<Map<String, String>> reducedPerfs) {
        allReducedPerfs.addAll(reducedPerfs);
    }

    //这里设计的不对，跟场景耦合了
    public List<Map<String, String>> getOverlapRisePerfsAndSizeEqual5() {
        //遍历overlapRisePerfs,将map.size不是5的舍弃
        for(int i = 0; i < allOverlapRisePerfs.size(); i++){
            if(allOverlapRisePerfs.get(i).size() != 5){
                allOverlapRisePerfs.remove(i);
            }
        }
        return allOverlapRisePerfs;
    }

    //用例名 耗时1 耗时2 要拼接成用例名 耗时1 耗时2 耗时3 耗时4
    public void mergeRisePerfs(List<Map<String, String>> risePerfs) {
        boolean key = false;
        if(allOverlapRisePerfs == null) allOverlapRisePerfs = risePerfs;
        //如果存在某个该用例则将耗时拼在结尾 否则的话，添加到集合中
        else {
            for (Map<String, String> risePerf : risePerfs) {
                for (Map<String, String> overlapRisePerf : allOverlapRisePerfs) {
                    String caseName = risePerf.get("caseName");
                    String overlapCaseName = overlapRisePerf.get("caseName");
                    if (caseName != null && caseName.equals(overlapCaseName)) {
                        long oldMeasureTime = Long.parseLong(risePerf.get("oldMeasureTime"));
                        String oldMeasureTimeName = "oldMeasureTime" + overlapRisePerf.size();
                        overlapRisePerf.put(oldMeasureTimeName, String.valueOf(oldMeasureTime));
                        key = true;
                        break;
                    }
                }
                if(!key){
                    allOverlapRisePerfs.add(risePerf);
                }
            }
        }
    }
}
