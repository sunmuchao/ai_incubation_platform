package ci.benchMark;

import java.util.ArrayList;
import java.util.List;

/**
 * @author sunmuchao
 * @date 2024/6/18 3:26 下午
 */
public class PriorityCoreClassesRs {
    private List<String> HighPriorityCoreClasses;
    private List<String> MediumPriorityCoreClasses;
    private List<String> LowPriorityCoreClasses;

    public PriorityCoreClassesRs(){
        HighPriorityCoreClasses = new ArrayList<>();
        MediumPriorityCoreClasses = new ArrayList<>();
        LowPriorityCoreClasses = new ArrayList<>();
    }

    public void setHighPriorityCoreClass(String highPriorityCoreClass){
        HighPriorityCoreClasses.add(highPriorityCoreClass);
    }

    public void setMediumPriorityCoreClass(String mediumPriorityCoreClass){
        MediumPriorityCoreClasses.add(mediumPriorityCoreClass);
    }

    public void setLowPriorityCoreClasses(String lowPriorityCoreClass){
        MediumPriorityCoreClasses.add(lowPriorityCoreClass);
    }

    public List<String> getHighPriorityCoreClasses() {
        return HighPriorityCoreClasses;
    }

    public List<String> getMediumPriorityCoreClasses() {
        return MediumPriorityCoreClasses;
    }

    public List<String> getLowPriorityCoreClasses() {
        return LowPriorityCoreClasses;
    }
}
