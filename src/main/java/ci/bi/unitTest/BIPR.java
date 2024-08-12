package ci.bi.unitTest;

import ci.benchMark.PR;
import lombok.Getter;
import lombok.Setter;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Getter
@Setter
public class BIPR extends PR {
    private final String repository;
    private final String fatherRepository;
    private Map<String,String> unionFactory;
    private String lastTriggerTime;
    private boolean isNeedToRunAll;
    private List<String> subModules;


    //一般pr对象
    public BIPR(String displayId, String builder, String prId,String repository,String fatherRepository) {
        super(displayId, builder, prId);
        this.repository=repository;
        this.fatherRepository=fatherRepository;
        unionFactory=new HashMap<>();
        isNeedToRunAll=false;
    }

    //适用于下载patch时的对象
    public BIPR(String repository,String fatherRepository, String prId){
        super(null,null,prId);
        this.repository=repository;
        this.fatherRepository=fatherRepository;
    }

}
