
'use strict';

void function() {
  /* The URL of this script (if available) for API endpoint auto-detection. */
  // This has to be fetched synchronously -- currentScript will be different
  // by the time init() is run.
  var thisURL = null;
  if (document.currentScript) thisURL = document.currentScript.src;
  /* The API's base URL. */
  var apiBaseURL = null;
  window.BellBotAPI = {
    /* Initialize the API endpoint.
     * scriptID is the ID of the <script> element via which the SDK was
     * loaded; the URLs of the API endpoints are derived from it.
     * baseOverride overrides the script-element-based auto-detection
     * mechanism to provide an explicit base URL. */
    init: function(scriptID, baseOverride) {
      var effScriptURL;
      if (baseOverride) {
        apiBaseURL = baseOverride;
        return;
      } else if (scriptID) {
        var script = document.getElementById(scriptID);
        if (! script) throw new Error('Cannot locate SDK script');
        effScriptURL = script.src;
      } else if (thisURL) {
        effScriptURL = thisURL;
      } else {
        throw new Error('Cannot locate API endpoints');
      }
      apiBaseURL = new URL('.', effScriptURL).href;
    }
  };
}();
