<?php

/**
 * @package     CrazyMidi.Administrator
 * @subpackage  com_ciggiecounter
 *
 * @copyright   (C) 2026 crazy-midi.de
 * @license     GPL-3.0-or-later
 */

namespace CrazyMidi\Component\Ciggiecounter\Administrator\View\Ciggiecounter;

defined('_JEXEC') or die;

use Joomla\CMS\Language\Text;
use Joomla\CMS\MVC\View\HtmlView as BaseHtmlView;
use Joomla\CMS\Toolbar\ToolbarHelper;

class HtmlView extends BaseHtmlView
{
    public function display($tpl = null)
    {
        ToolbarHelper::title(Text::_('COM_CIGGIECOUNTER'), 'home');

        parent::display($tpl);
    }
}
