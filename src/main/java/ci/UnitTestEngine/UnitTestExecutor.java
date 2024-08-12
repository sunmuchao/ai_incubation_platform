package ci.UnitTestEngine;

import base.cmd.ShellTool;
import base.third.bitBucket.BitBucketUtils;
import ci.benchMark.TaskStatusManagement;

import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * @author sunmuchao
 * @date 2024/8/5 3:22 下午
 */
public class UnitTestExecutor {
    public static void main(String[] args) throws Exception {
        String uuid = args[0];
        String prId = args[1];
        Path projectPath = Paths.get(args[2]);
        Path ExecutionPath = Paths.get(args[3]);
        String jobName = args[4];
        int documentNumber = Integer.parseInt(args[5]);
        boolean isContainBIChange = Boolean.parseBoolean(args[6]);
        boolean isContainHihidataChange = Boolean.parseBoolean(args[7]);

        UnitTestTaskInformation utti = new UnitTestTaskInformation(uuid, prId)
                .setContainBIChange(isContainBIChange)
                .setContainHihidataChange(isContainHihidataChange)
                .setDocumentNumber(documentNumber);

        String containerName = jobName;
        String caseFileName = utti.getUuid() + "_" + jobName + "_" + utti.getDocumentNumber() + ".txt";

        Path BinPath = projectPath.resolve("bin");
        Path CodeStoragePath = projectPath.resolve("CodeStorage").resolve(uuid);
        Path CIInformationPath = projectPath.resolve("CIInformation");
        Path CIInformation = CIInformationPath.resolve(caseFileName);

        BitBucketUtils bbu = new BitBucketUtils(prId);
        TaskStatusManagement tsm = new TaskStatusManagement(uuid, prId);
        if(tsm.isHasNewerRecurringTask() || !bbu.PrIsOpen()){
            tsm.modifyStatus2Cancel();
            //则取消任务
            return;
        }else{
            //继续执行任务
            //将项目从CodeStorage拷贝到执行目录下
            String shell1 = "cp -r " + CodeStoragePath + "/* " + ExecutionPath;
            ShellTool.cmd(shell1);
            //执行指定模块的单测任务
            Path UnitTestOperatorPath = BinPath.resolve("UnitTestOperator.sh");
            String shell2 = "sh " + UnitTestOperatorPath  + " " + CIInformation.toString() + " " + containerName + " " + isContainBIChange + " " + isContainHihidataChange;
            ShellTool.cmd(shell2);
            //将所有项目下的target/surefire-reports 拷贝到CodeStorage下的对应uuid目录下
            Path copyFinalPath = BinPath.resolve("copyFinal.sh");
            String shell3 = "sh " + copyFinalPath + " " + ExecutionPath + " " + CodeStoragePath;
            ShellTool.cmd(shell3);
        }
    }
}
