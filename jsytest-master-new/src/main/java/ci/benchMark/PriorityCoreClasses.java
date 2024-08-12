package ci.benchMark;

import java.util.List;

/**
 * @author sunmuchao
 * @date 2024/6/18 11:54 上午
 */
public class PriorityCoreClasses {
    private List<String> HighPriorityCoreClasses;
    private List<String> MediumPriorityCoreClasses;
    private List<String> LowPriorityCoreClasses;
    private PriorityCoreClassesRs pccrs;


    public void setHighPriorityCoreClasses(List<String> highPriorityCoreClasses) {
        HighPriorityCoreClasses = highPriorityCoreClasses;
    }

    public void setMediumPriorityCoreClasses(List<String> mediumPriorityCoreClasses) {
        MediumPriorityCoreClasses = mediumPriorityCoreClasses;
    }

    public void setLowPriorityCoreClasses(List<String> lowPriorityCoreClasses) {
        LowPriorityCoreClasses = lowPriorityCoreClasses;
    }

    public void JudgePriority(String className) {
        if (pccrs == null) {
            pccrs = new PriorityCoreClassesRs();
        }

        if(HighPriorityCoreClasses != null) {
            for (String hpcc : HighPriorityCoreClasses) {
                if (className.contains(hpcc)) {
                    pccrs.setHighPriorityCoreClass(hpcc);
                }
            }
        }

        if(MediumPriorityCoreClasses != null) {
            for (String hpcc : MediumPriorityCoreClasses) {
                if (className.contains(hpcc)) {
                    pccrs.setMediumPriorityCoreClass(hpcc);
                }
            }
        }

        if(LowPriorityCoreClasses != null) {
            for (String hpcc : LowPriorityCoreClasses) {
                if (className.contains(hpcc)) {
                    pccrs.setLowPriorityCoreClasses(hpcc);
                }
            }
        }
    }

    public PriorityCoreClassesRs getPriorityCoreClassesRs() {
        return pccrs;
    }
}