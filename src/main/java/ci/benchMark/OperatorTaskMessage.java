package ci.benchMark;

import com.fasterxml.jackson.annotation.JsonProperty;

public class OperatorTaskMessage {
        @JsonProperty("uuid")
        private String uuid;

        @JsonProperty("prId")
        private String prId;

        // Getters and setters (you can generate these or write manually)
        public String getUuid() {
            return uuid;
        }

        public void setUuid(String uuid) {
            this.uuid = uuid;
        }

        public String getPrId() {
            return prId;
        }

        public void setPrId(String prId) {
            this.prId = prId;
        }
    }
