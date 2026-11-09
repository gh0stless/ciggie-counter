<?php

/**
 * @package     CrazyMidi.Site
 * @subpackage  com_ciggiecounter
 *
 * @copyright   (C) 2026 crazy-midi.de
 * @license     GPL-3.0-or-later
 */

namespace CrazyMidi\Component\Ciggiecounter\Site\View\Ciggiecounter;

defined('_JEXEC') or die;

use Joomla\CMS\Language\Text;
use Joomla\CMS\MVC\View\HtmlView as BaseHtmlView;

class HtmlView extends BaseHtmlView
{
    public function display($tpl = null)
    {
        $document = $this->getDocument();
        $document->setTitle(Text::_('COM_CIGGIECOUNTER_PAGE_TITLE'));
        $document->setDescription(Text::_('COM_CIGGIECOUNTER_META_DESCRIPTION'));
        // eigene Gestaltung, nur für diese Seite; keine externen Schriften (DSGVO)
        $document->getWebAssetManager()->registerAndUseStyle(
            'com_ciggiecounter.style',
            'media/com_ciggiecounter/css/style.css',
            ['version' => '1.0.6']
        );

        parent::display($tpl);
    }
}
