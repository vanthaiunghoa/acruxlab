odoo.define('whatsapp_connector.chat_classes', function(require) {
"use strict";

/**
 Se une todas las clases en una sola para ser más fácil de consultar
 */

return {
    Message: require('whatsapp_connector.message'),
    Conversation: require('whatsapp_connector.conversation'),
    ToolBox: require('whatsapp_connector.toolbox'),
    DefaultAnswer: require('whatsapp_connector.default_answer'),
    ProductSearch: require('whatsapp_connector.product_search'),
    InitConversation: require('whatsapp_connector.init_conversation'),
    UserStatus: require('whatsapp_connector.user_status'),
    ResPartnerForm: require('whatsapp_connector.res_partner'),
    ConversationForm: require('whatsapp_connector.conversation_form'),
};
});