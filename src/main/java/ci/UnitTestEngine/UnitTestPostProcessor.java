package ci.UnitTestEngine;

import base.third.bitBucket.BitBucketUtils;
import ci.benchMark.UnitTestTaskManager;

import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * @author sunmuchao
 * @date 2024/8/7 5:17 下午
 */
public class UnitTestPostProcessor {
    public static void main(String[] args) throws Exception {
        String uuid = args[0];
        String operatorNodeName = args[1];
        Path projectPath = Paths.get(args[2]);
        String builder = args[3];
        String prId = args[4];
        String branch = args[5];
        int documentNumber = Integer.parseInt(args[6]);
        boolean isContainBIChange = Boolean.parseBoolean(args[7]);
        boolean isContainHihidataChange = Boolean.parseBoolean(args[8]);
        Path jenkinsToolPath = projectPath.resolve("bin").resolve("jenkinsTool");

        BitBucketUtils bbu = new BitBucketUtils(prId);

        UnitTestTaskInformation utti = new UnitTestTaskInformation(uuid, prId)
                .setContainBIChange(isContainBIChange)
                .setContainHihidataChange(isContainHihidataChange)
                .setDocumentNumber(documentNumber)
                .addOperatorNodeName(operatorNodeName)
                .setBuilder(builder)
                .setBranch(branch);

        if(bbu.PrIsOpen()){
            UnitTestTaskManager uttm = new UnitTestTaskManager(utti);
            uttm.manage();
        }
    }
}
