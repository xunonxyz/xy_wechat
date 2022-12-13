/** @odoo-module */

import {registry} from "@web/core/registry";

const {Component, xml, useEffect, onWillStart} = owl;
import {loadJS} from "@web/core/assets";
import {useService} from "@web/core/utils/hooks";

class WEQrcode extends Component {
    setup() {
        this.rpc = useService("rpc");

        onWillStart(() => loadJS("http://wwcdn.weixin.qq.com/node/wework/wwopen/js/wwLogin-1.2.7.js"));

        useEffect(async () => {
            // to safety, we can not request by search_read, so we use rpc
            const app = await this.rpc('/we/oauth2/info', {
                app_id: this.props.appId
            })

            new WwLogin({
                "id": "wx_reg",
                "appid": app.corp_id,
                "agentid": app.agentid,
                "redirect_uri": encodeURIComponent(app.redirect_uri),
            });
        }, () => [])
    }
}

WEQrcode.template = xml`
<div style="width: 100%;height: 100%">
    <div id="wx_reg" style="width: 100%;height: 100%;display: flex;justify-content: center;align-items: center;"></div>
</div>
`;

WEQrcode.defaultProps = {
    appId: "",
};
WEQrcode.extractProps = ({attrs}) => {
    return {
        appId: attrs.app_id,
    };
};

registry.category("view_widgets").add("we_qrcode", WEQrcode);

export default WEQrcode;
